from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from common.utils import api_response
from .models import Incident, IncidentTimeline
from .serializers import IncidentSerializer
from emergency.models import ResponderUnit
from accounts.permissions import authority_required, IsAuthority


def broadcast_to_c2(event_type, payload):
    """Helper to send real-time events to the C2 Command Operations channel."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "c2_operations_feed",
                {
                    "type": "c2_broadcast_event",
                    "data": {
                        "type": event_type,
                        "timestamp": timezone.now().isoformat(),
                        **payload
                    }
                }
            )
    except Exception as e:
        print(f"WebSocket broadcast error: {e}")


@authority_required
def incidents_c2_view(request):
    """
    Authority C2 Incident Management & Triage Center.
    Provides comprehensive filtering by category, severity, status, responder assignment, and resolution.
    """
    queryset = Incident.objects.all().order_by('-created_at')

    # Apply filters
    cat = request.GET.get('category')
    sev = request.GET.get('severity')
    stat = request.GET.get('status')

    if cat:
        queryset = queryset.filter(category=cat)
    if sev:
        queryset = queryset.filter(severity=sev)
    if stat:
        queryset = queryset.filter(status=stat)

    responders = ResponderUnit.objects.exclude(status='OFF_DUTY').order_by('agency', 'callsign')

    return render(request, 'authority/incidents.html', {
        'incidents': queryset,
        'responders': responders,
        'categories': Incident.CATEGORY_CHOICES,
        'severities': Incident.SEVERITY_CHOICES,
        'statuses': Incident.STATUS_CHOICES,
        'selected_category': cat,
        'selected_severity': sev,
        'selected_status': stat,
    })


@login_required
def tourist_report_view(request):
    """
    Tourist Progressive Incident & Hazard Reporting Interface.
    Organized into 3 simple, non-overwhelming progressive steps:
      Step 1: Category & Priority Quick-Select Chips
      Step 2: Location Auto-Fill (GPS) & Landmark
      Step 3: Brief Details & Optional Secure Photo/Video Evidence
    """
    if request.method == 'POST':
        category = request.POST.get('category', 'OTHER')
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')
        location_name = request.POST.get('location_name', 'Current Location')
        severity = request.POST.get('severity', 'MEDIUM')
        image = request.FILES.get('evidence_image')

        # Auto-generate title if left blank
        if not title:
            dict_cat = dict(Incident.CATEGORY_CHOICES)
            title = f"{dict_cat.get(category, 'Incident')} reported at {location_name}"

        # Fallback to tourist profile coordinates
        if not lat or not lng:
            profile = getattr(request.user, 'tourist_profile', None)
            if profile:
                lat = profile.current_latitude or 15.4989
                lng = profile.current_longitude or 73.8278

        incident = Incident.objects.create(
            reporter=request.user,
            reporter_name=request.user.get_full_name() or request.user.username,
            reporter_phone=request.user.phone_number,
            category=category,
            severity=severity,
            title=title,
            description=description,
            latitude=float(lat),
            longitude=float(lng),
            location_name=location_name,
            evidence_image=image
        )

        IncidentTimeline.objects.create(
            incident=incident,
            status='REPORTED',
            note="Incident filed by tourist via mobile portal.",
            actor=request.user
        )

        # Broadcast live event to C2 operations room
        broadcast_to_c2("incident_created", {
            "incident": IncidentSerializer(incident).data
        })

        messages.success(request, f"Incident filed successfully. Case ID: {incident.incident_id}. Tourism Police & C2 Desk notified.")
        return redirect('incidents:incident_detail', incident_id=incident.incident_id)

    return render(request, 'tourist/report_incident.html', {
        'categories': Incident.CATEGORY_CHOICES,
        'severities': Incident.SEVERITY_CHOICES,
    })


def incidents_public_feed_view(request):
    """
    Public & Tourist Community Safety Incidents & Hazard Feed.
    Allows tourists and citizens to view reported community safety hazards,
    track the resolution status of their own reports, and locate hazards on the map.
    """
    all_incidents = Incident.objects.exclude(status='FALSE_ALARM').order_by('-created_at')

    cat = request.GET.get('category')
    sev = request.GET.get('severity')
    stat = request.GET.get('status')

    if cat:
        all_incidents = all_incidents.filter(category=cat)
    if sev:
        all_incidents = all_incidents.filter(severity=sev)
    if stat:
        all_incidents = all_incidents.filter(status=stat)

    my_incidents = []
    if request.user.is_authenticated:
        my_incidents = Incident.objects.filter(reporter=request.user).order_by('-created_at')

    return render(request, 'tourist/incidents_feed.html', {
        'incidents': all_incidents,
        'my_incidents': my_incidents,
        'categories': Incident.CATEGORY_CHOICES,
        'severities': Incident.SEVERITY_CHOICES,
        'statuses': Incident.STATUS_CHOICES,
        'selected_category': cat,
        'selected_severity': sev,
        'selected_status': stat,
    })


def incident_detail_view(request, incident_id):
    """
    Detailed view for a specific safety incident / hazard report.
    Displays location, timeline, status updates, and interactive map locator.
    """
    incident = get_object_or_404(Incident, incident_id=incident_id)
    timeline = incident.timeline.all().order_by('timestamp')

    return render(request, 'tourist/incident_detail.html', {
        'incident': incident,
        'timeline': timeline,
    })


# ==============================================================================
# REST API Endpoints
# ==============================================================================

class IncidentListCreateAPIView(APIView):
    """
    List active incidents or file a new incident report.
    Supports filtering by status, category, and severity.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = Incident.objects.all().order_by('-created_at')
        status_filter = request.query_params.get('status')
        category_filter = request.query_params.get('category')
        severity_filter = request.query_params.get('severity')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        if severity_filter:
            queryset = queryset.filter(severity=severity_filter)

        serializer = IncidentSerializer(queryset[:60], many=True)
        return api_response(success=True, message="Incidents retrieved", data=serializer.data)

    def post(self, request):
        serializer = IncidentSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user if request.user.is_authenticated else None
            incident = serializer.save(reporter=user)

            IncidentTimeline.objects.create(
                incident=incident,
                status='REPORTED',
                note="Incident reported into system.",
                actor=user
            )

            # Broadcast live event to C2
            broadcast_to_c2("incident_created", {
                "incident": IncidentSerializer(incident).data
            })

            return api_response(success=True, message="Incident reported successfully", data=IncidentSerializer(incident).data, http_code=status.HTTP_201_CREATED)
        return api_response(success=False, message="Validation error", errors=serializer.errors, http_code=status.HTTP_400_BAD_REQUEST)


class IncidentDetailUpdateAPIView(APIView):
    """
    Authority endpoint to retrieve, assign, triage, update status, add notes, and resolve an incident.
    """
    permission_classes = [IsAuthority]

    def get(self, request, incident_id):
        incident = get_object_or_404(Incident, incident_id=incident_id)
        return api_response(success=True, data=IncidentSerializer(incident).data)

    def patch(self, request, incident_id):
        incident = get_object_or_404(Incident, incident_id=incident_id)
        new_status = request.data.get('status')
        new_severity = request.data.get('severity')
        assigned_unit_id = request.data.get('assigned_responder_id')
        resolution_notes = request.data.get('resolution_notes')
        note = request.data.get('timeline_note', '')

        if new_status and new_status != incident.status:
            incident.status = new_status
            if new_status == 'RESOLVED':
                incident.resolved_at = timezone.now()
            IncidentTimeline.objects.create(
                incident=incident,
                status=new_status,
                note=note or f"Status transitioned to {incident.get_status_display()}",
                actor=request.user if request.user.is_authenticated else None
            )

        if new_severity:
            incident.severity = new_severity

        if assigned_unit_id:
            responder = ResponderUnit.objects.filter(id=assigned_unit_id).first()
            if responder:
                incident.assigned_responder = responder
                if not new_status or new_status in ['REPORTED', 'VERIFIED']:
                    incident.status = 'ASSIGNED'
                responder.status = 'DISPATCHED'
                responder.save(update_fields=['status'])
                IncidentTimeline.objects.create(
                    incident=incident,
                    status='ASSIGNED',
                    note=f"Assigned to {responder.callsign} ({responder.get_agency_display()})",
                    actor=request.user if request.user.is_authenticated else None
                )
        elif 'assigned_responder_id' in request.data and not request.data.get('assigned_responder_id'):
            incident.assigned_responder = None

        if resolution_notes:
            incident.resolution_notes = resolution_notes

        incident.save()

        # Broadcast live status update to C2
        assigned_callsign = incident.assigned_responder.callsign if incident.assigned_responder else None
        broadcast_to_c2("incident_status_changed", {
            "incident_id": incident.incident_id,
            "status": incident.status,
            "severity": incident.severity,
            "assigned_responder": assigned_callsign,
            "incident": IncidentSerializer(incident).data
        })

        return api_response(
            success=True,
            message="Incident record updated successfully",
            data=IncidentSerializer(incident).data
        )
