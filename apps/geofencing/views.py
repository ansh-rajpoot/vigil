from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from common.utils import api_response
from .models import GeoZone, GeofenceBreachLog, TouristZonePresence
from .serializers import GeoZoneSerializer, GeofenceBreachLogSerializer
from .engine import process_tourist_geofence_transitions
from tourists.models import TouristProfile
from accounts.permissions import authority_required, IsAuthority


@authority_required
def geofence_manager_view(request):
    """Authority C2 Geo-Fence Manager to view, create, update, and toggle active status of spatial zones."""
    zones = GeoZone.objects.all().order_by('-created_at')
    active_breaches = GeofenceBreachLog.objects.filter(is_acknowledged=False).order_by('-timestamp')[:15]

    return render(request, 'authority/geofence_mgr.html', {
        'zones': zones,
        'active_breaches': active_breaches
    })


# ==============================================================================
# REST API Endpoints
# ==============================================================================

class GeoZoneListCreateAPIView(APIView):
    """API to fetch all active geofences and allow authorities to create new zones."""
    permission_classes = [AllowAny]

    def get(self, request):
        zones = GeoZone.objects.filter(is_active=True)
        serializer = GeoZoneSerializer(zones, many=True)
        return api_response(success=True, message="Active geo-zones fetched", data=serializer.data)

    def post(self, request):
        if not request.user.is_authenticated or not request.user.is_operator:
            return api_response(success=False, message="Unauthorized. Operator credentials required.", http_code=status.HTTP_403_FORBIDDEN)

        serializer = GeoZoneSerializer(data=request.data)
        if serializer.is_valid():
            zone = serializer.save()
            return api_response(success=True, message=f"Geo-zone '{zone.name}' created successfully", data=serializer.data, http_code=status.HTTP_201_CREATED)
        return api_response(success=False, message="Validation error", errors=serializer.errors, http_code=status.HTTP_400_BAD_REQUEST)


class GeoZoneDetailAPIView(APIView):
    """Authority endpoint to retrieve, update, or toggle active status of a specific zone."""
    permission_classes = [IsAuthority]

    def get(self, request, zone_id):
        zone = get_object_or_404(GeoZone, id=zone_id)
        return api_response(success=True, data=GeoZoneSerializer(zone).data)

    def patch(self, request, zone_id):
        zone = get_object_or_404(GeoZone, id=zone_id)
        serializer = GeoZoneSerializer(zone, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response(success=True, message=f"Zone '{zone.name}' updated successfully", data=serializer.data)
        return api_response(success=False, errors=serializer.errors, http_code=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, zone_id):
        zone = get_object_or_404(GeoZone, id=zone_id)
        zone.is_active = False
        zone.save(update_fields=['is_active'])
        return api_response(success=True, message=f"Zone '{zone.name}' deactivated successfully")


class CheckLocationContainmentAPIView(APIView):
    """
    Evaluates tourist location against all active geofence zones.
    Executes entry/exit detection, dynamic risk recalculation, and duplicate alert suppression.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        tourist_id = request.data.get('tourist_id')

        if lat is None or lng is None:
            return api_response(success=False, message="Latitude and Longitude required", http_code=status.HTTP_400_BAD_REQUEST)

        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            return api_response(success=False, message="Invalid coordinate format", http_code=status.HTTP_400_BAD_REQUEST)

        tourist = None
        if tourist_id:
            tourist = TouristProfile.objects.filter(id=tourist_id).first()
        elif request.user.is_authenticated and hasattr(request.user, 'tourist_profile'):
            tourist = request.user.tourist_profile

        if not tourist:
            # Evaluate without persistence
            active_zones = GeoZone.objects.filter(is_active=True)
            containing = [
                {'id': z.id, 'name': z.name, 'zone_type': z.zone_type, 'color': z.get_color_hex(), 'safety_advisory': z.safety_advisory}
                for z in active_zones if z.contains_point(lat, lng)
            ]
            return api_response(success=True, data={'is_in_any_zone': len(containing) > 0, 'containing_zones': containing})

        # Process full transition workflow with state tracking and duplicate alert suppression
        result = process_tourist_geofence_transitions(tourist, lat, lng)
        return api_response(success=True, message="Geofence transitions processed", data=result)


class AcknowledgeBreachAPIView(APIView):
    permission_classes = [IsAuthority]

    def post(self, request, breach_id):
        breach = get_object_or_404(GeofenceBreachLog, id=breach_id)
        breach.is_acknowledged = True
        breach.acknowledged_by = request.user
        breach.action_taken = request.data.get('action_taken', 'Investigated and cleared by C2 Command Desk.')
        breach.resolved_at = timezone.now()
        breach.save()

        return api_response(success=True, message="Breach log marked as resolved", data=GeofenceBreachLogSerializer(breach).data)
