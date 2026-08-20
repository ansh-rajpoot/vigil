from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from common.utils import api_response
from .models import TouristProfile, TouristLocationHistory
from .serializers import TouristProfileSerializer
from risk.models import TouristRiskAssessment, Blackspot
from geofencing.models import GeoZone
from alerts.models import EmergencyBroadcast
from digital_id.models import DigitalTouristID
from incidents.models import Incident


@login_required
def home_view(request):
    if request.user.is_operator:
        return redirect('dashboard:c2_command')

    # Get or create tourist profile
    profile, created = TouristProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'nationality': 'Indian',
            'destination_city': 'Greater Noida & Noida, NCR',
            'current_latitude': 28.4744,
            'current_longitude': 77.5040,
            'last_location_time': timezone.now()
        }
    )

    # Get Digital ID
    digital_id = DigitalTouristID.objects.filter(tourist=profile).first()

    # Get latest risk assessment
    latest_risk = TouristRiskAssessment.objects.filter(tourist=profile).order_by('-evaluated_at').first()
    if not latest_risk:
        latest_risk = TouristRiskAssessment.objects.create(
            tourist=profile,
            overall_score=12,
            risk_level='SAFE',
            primary_risk_factor="Normal Tourist Corridor",
            ai_recommendation="Area has strong tourist police coverage and CCTV surveillance."
        )

    # Nearby active safety zones
    safe_zones = GeoZone.objects.filter(is_active=True)[:4]

    # Active Non-Expired Emergency Broadcasts
    now = timezone.now()
    active_alerts = EmergencyBroadcast.objects.filter(is_active=True, starts_at__lte=now, expires_at__gte=now).order_by('-created_at')[:3]

    # Active Community Safety Hazards & Incidents
    recent_incidents = Incident.objects.exclude(status='FALSE_ALARM').order_by('-created_at')[:4]

    # Emergency Contacts
    emergency_contacts = request.user.emergency_contacts.all()

    context = {
        'profile': profile,
        'digital_id': digital_id,
        'risk': latest_risk,
        'safe_zones': safe_zones,
        'active_alerts': active_alerts,
        'recent_incidents': recent_incidents,
        'emergency_contacts': emergency_contacts,
        'now': timezone.now()
    }
    return render(request, 'tourist/home.html', context)


@login_required
def profile_view(request):
    profile = get_object_or_404(TouristProfile, user=request.user)

    if request.method == 'POST':
        profile.nationality = request.POST.get('nationality', profile.nationality)
        profile.blood_group = request.POST.get('blood_group', profile.blood_group)
        profile.medical_conditions = request.POST.get('medical_conditions', profile.medical_conditions)
        profile.allergies = request.POST.get('allergies', profile.allergies)
        profile.hotel_stay_details = request.POST.get('hotel_stay_details', profile.hotel_stay_details)
        profile.destination_city = request.POST.get('destination_city', profile.destination_city)
        profile.save()
        messages.success(request, "Safety & medical profile updated successfully.")
        return redirect('tourists:profile')

    return render(request, 'tourist/profile.html', {
        'profile': profile,
        'emergency_contacts': request.user.emergency_contacts.all()
    })


# API Endpoints
from rest_framework.permissions import AllowAny, IsAuthenticated

class UpdateLocationAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        profile = getattr(request.user, 'tourist_profile', None) if request.user.is_authenticated else None
        if not profile:
            profile = TouristProfile.objects.filter(user__username='tourist_ananya').first()
            if not profile:
                profile = TouristProfile.objects.first()
        if not profile:
            return api_response(success=False, message="Tourist profile not found", http_code=status.HTTP_404_NOT_FOUND)

        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        battery = request.data.get('battery_level', 95)
        speed = request.data.get('speed', 0.0)
        accuracy = request.data.get('accuracy', 5.0)

        if lat is None or lng is None:
            return api_response(success=False, message="Latitude and Longitude required", http_code=status.HTTP_400_BAD_REQUEST)

        try:
            new_lat = float(lat)
            new_lng = float(lng)
            battery_val = int(battery) if battery is not None else 95
            accuracy_val = float(accuracy) if accuracy is not None else 5.0
            speed_val = float(speed) if speed is not None else 0.0
        except (ValueError, TypeError):
            return api_response(success=False, message="Invalid numerical format for coordinates or telemetry", http_code=status.HTTP_400_BAD_REQUEST)

        if not (-90.0 <= new_lat <= 90.0) or not (-180.0 <= new_lng <= 180.0):
            return api_response(success=False, message="Coordinates out of valid geographical bounds (-90 to 90, -180 to 180)", http_code=status.HTTP_400_BAD_REQUEST)

        battery_val = max(0, min(100, battery_val))
        accuracy_val = max(0.1, accuracy_val)

        profile.current_latitude = new_lat
        profile.current_longitude = new_lng
        profile.battery_level = battery_val
        profile.last_location_time = timezone.now()
        profile.save(update_fields=['current_latitude', 'current_longitude', 'battery_level', 'last_location_time'])

        # Sensible update interval: avoid creating a history log every second
        last_log = TouristLocationHistory.objects.filter(tourist=profile).order_by('-timestamp').first()
        should_record_log = True
        if last_log:
            time_diff_sec = (timezone.now() - last_log.timestamp).total_seconds()
            from common.utils import haversine_distance
            dist_moved_meters = haversine_distance(last_log.latitude, last_log.longitude, new_lat, new_lng) * 1000.0
            # Only record if at least 15 seconds elapsed OR tourist moved > 15 meters
            if time_diff_sec < 15.0 and dist_moved_meters < 15.0:
                should_record_log = False

        if should_record_log:
            TouristLocationHistory.objects.create(
                tourist=profile,
                latitude=new_lat,
                longitude=new_lng,
                speed=float(speed),
                battery_level=int(battery),
                accuracy=float(accuracy)
            )

        # Evaluate real-time geofence transitions & alerts
        from geofencing.engine import process_tourist_geofence_transitions
        geofence_events = process_tourist_geofence_transitions(profile, new_lat, new_lng)

        return api_response(success=True, message="Location heartbeat updated", data={
            'latitude': profile.current_latitude,
            'longitude': profile.current_longitude,
            'battery_level': profile.battery_level,
            'last_location_time': profile.last_location_time.isoformat(),
            'geofence_events': geofence_events
        })


class SafeCheckinAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = getattr(request.user, 'tourist_profile', None)
        if not profile:
            return api_response(success=False, message="Tourist profile not found", http_code=status.HTTP_404_NOT_FOUND)

        profile.last_safe_checkin = timezone.now()
        profile.save(update_fields=['last_safe_checkin'])

        return api_response(success=True, message="Safety check-in recorded successfully", data={
            'last_safe_checkin': profile.last_safe_checkin.isoformat()
        })
