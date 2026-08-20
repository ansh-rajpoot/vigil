from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from common.utils import api_response, haversine_distance
from .models import SOSAlert, ResponderUnit, SOSDispatch, SOSLiveBreadcrumb
from .serializers import SOSAlertSerializer, ResponderUnitSerializer, SOSDispatchSerializer
from tourists.models import TouristProfile
from accounts.permissions import IsAuthority, authority_required


@authority_required
def fleet_manager_view(request):
    """
    Authority C2 PCR Van & Emergency Responder Fleet Management Portal.
    Allows real-time GPS tracking of all patrol units, live location updates,
    status toggles, unit dispatches, and registration of new PCR vans.
    """
    responders = ResponderUnit.objects.all().order_by('agency', 'unit_code')
    total_units = responders.count()
    available_units = responders.filter(status='AVAILABLE').count()
    dispatched_units = responders.filter(status__in=['DISPATCHED', 'ON_SCENE']).count()
    off_duty_units = responders.filter(status='OFF_DUTY').count()

    return render(request, 'authority/fleet_manager.html', {
        'responders': responders,
        'total_units': total_units,
        'available_units': available_units,
        'dispatched_units': dispatched_units,
        'off_duty_units': off_duty_units,
        'agency_choices': ResponderUnit.AGENCY_CHOICES,
        'status_choices': ResponderUnit.STATUS_CHOICES,
    })


@login_required
def sos_active_view(request, sos_id):
    """
    Tourist live emergency beacon HUD view.
    Displays live responder telemetry, ETA countdown, emergency contacts, and cancellation action.
    """
    sos = get_object_or_404(SOSAlert, sos_id=sos_id)
    emergency_contacts = request.user.emergency_contacts.all()
    dispatches = sos.dispatches.all().order_by('-dispatched_at')

    return render(request, 'tourist/sos_active.html', {
        'sos': sos,
        'emergency_contacts': emergency_contacts,
        'dispatches': dispatches,
    })


# ==============================================================================
# REST API Endpoints
# ==============================================================================

class TriggerSOSAPIView(APIView):
    """
    Triggers immediate SOS emergency alert.
    1. Captures GPS location & accuracy.
    2. Records Tourist ID & timestamp.
    3. Prevents accidental duplicate requests if an active SOS is already in progress.
    4. Finds nearby emergency services (PCR Vans, Tourism Police, 108 EMS).
    5. Dispatches notifications over Django Channels WebSockets to C2 Operation Room.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        trigger_type = request.data.get('trigger_type', 'MANUAL_BUTTON')
        emergency_notes = request.data.get('emergency_notes', '')
        battery = request.data.get('battery_level', 90)
        location_address = request.data.get('location_address', 'Current GPS Position')
        tourist_id = request.data.get('tourist_id')

        tourist = None
        if tourist_id:
            tourist = TouristProfile.objects.filter(id=tourist_id).first()
        elif request.user.is_authenticated and hasattr(request.user, 'tourist_profile'):
            tourist = request.user.tourist_profile

        if not tourist:
            return api_response(success=False, message="Tourist profile required to trigger SOS", http_code=status.HTTP_400_BAD_REQUEST)

        # Coordinate resolution
        if lat is None or lng is None:
            lat = tourist.current_latitude or 28.4744
            lng = tourist.current_longitude or 77.5040

        lat = float(lat)
        lng = float(lng)

        # Update tourist status
        tourist.trip_status = 'SOS_ACTIVE'
        tourist.current_latitude = lat
        tourist.current_longitude = lng
        tourist.last_location_time = timezone.now()
        tourist.save(update_fields=['trip_status', 'current_latitude', 'current_longitude', 'last_location_time'])

        # Check for existing in-progress SOS emergency to prevent duplicate popup cards
        existing_sos = SOSAlert.objects.filter(
            tourist=tourist,
            status__in=['ACTIVE', 'ACKNOWLEDGED', 'RESPONDING']
        ).order_by('-triggered_at').first()

        if existing_sos:
            existing_sos.latitude = lat
            existing_sos.longitude = lng
            existing_sos.battery_level = int(battery)
            if emergency_notes:
                existing_sos.emergency_notes = emergency_notes
            existing_sos.save(update_fields=['latitude', 'longitude', 'battery_level', 'emergency_notes'])

            SOSLiveBreadcrumb.objects.create(
                sos=existing_sos,
                latitude=lat,
                longitude=lng,
                speed=0.0,
                battery_level=int(battery)
            )

            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    "c2_operations_feed",
                    {
                        "type": "c2_broadcast_event",
                        "data": {
                            "type": "sos_location_updated",
                            "sos_id": existing_sos.sos_id,
                            "latitude": lat,
                            "longitude": lng,
                            "battery_level": int(battery),
                            "timestamp": timezone.now().isoformat()
                        }
                    }
                )

            return api_response(
                success=True,
                message="SOS position & telemetry updated for active emergency.",
                data=SOSAlertSerializer(existing_sos).data,
                http_code=status.HTTP_200_OK
            )

        # Create SOS emergency record
        sos = SOSAlert.objects.create(
            tourist=tourist,
            status='ACTIVE',
            trigger_type=trigger_type,
            latitude=lat,
            longitude=lng,
            battery_level=int(battery),
            location_address=location_address,
            emergency_notes=emergency_notes
        )

        # Initial live breadcrumb
        SOSLiveBreadcrumb.objects.create(
            sos=sos,
            latitude=lat,
            longitude=lng,
            speed=0.0,
            battery_level=int(battery)
        )

        # Find nearest available emergency responder unit
        responders = ResponderUnit.objects.filter(status='AVAILABLE')
        nearest_responder = None
        min_dist = float('inf')

        for r in responders:
            d = haversine_distance(lat, lng, r.current_latitude, r.current_longitude)
            if d < min_dist:
                min_dist = d
                nearest_responder = r

        # Auto-link nearest responder if within 12 km
        if nearest_responder and min_dist <= 12.0:
            eta = max(2, int(min_dist * 2.5))  # Estimate 2.5 mins per km
            SOSDispatch.objects.create(
                sos=sos,
                responder=nearest_responder,
                eta_minutes=eta,
                dispatch_status='ASSIGNED',
                notes=f"Auto-assigned nearest unit ({min_dist:.1f} km away)"
            )
            nearest_responder.status = 'DISPATCHED'
            nearest_responder.save(update_fields=['status'])
            sos.status = 'RESPONDING'
            sos.save(update_fields=['status'])

        # Broadcast WebSocket alert to C2 Command Center
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "c2_operations_feed",
                {
                    "type": "c2_broadcast_event",
                    "data": {
                        "type": "new_sos_alert",
                        "sos": SOSAlertSerializer(sos).data,
                        "timestamp": timezone.now().isoformat()
                    }
                }
            )

        return api_response(
            success=True,
            message="SOS Emergency Triggered. Responders & C2 Command Center alerted.",
            data=SOSAlertSerializer(sos).data,
            http_code=status.HTTP_201_CREATED
        )


class AcknowledgeSOSAPIView(APIView):
    """Authority C2 operator acknowledges an active SOS emergency."""
    permission_classes = [IsAuthority]

    def post(self, request, sos_id):
        sos = get_object_or_404(SOSAlert, sos_id=sos_id)
        sos.status = 'ACKNOWLEDGED'
        sos.acknowledged_at = timezone.now()
        sos.save(update_fields=['status', 'acknowledged_at'])

        # Broadcast update
        channel_layer = get_channel_layer()
        if channel_layer:
            payload = {
                "type": "sos_status_change",
                "sos_id": sos.sos_id,
                "status": "ACKNOWLEDGED",
                "officer_name": request.user.get_full_name() or request.user.username,
                "timestamp": timezone.now().isoformat()
            }
            async_to_sync(channel_layer.group_send)(
                f"sos_beacon_{sos.sos_id}",
                {"type": "sos_channel_message", "data": payload}
            )
            async_to_sync(channel_layer.group_send)(
                "c2_operations_feed",
                {"type": "c2_broadcast_event", "data": payload}
            )

        return api_response(success=True, message=f"Emergency {sos.sos_id} acknowledged by C2 operator", data=SOSAlertSerializer(sos).data)


class RespondSOSAPIView(APIView):
    """Authority C2 operator assigns or updates responder deployment for an active SOS."""
    permission_classes = [IsAuthority]

    def post(self, request, sos_id):
        sos = get_object_or_404(SOSAlert, sos_id=sos_id)
        responder_id = request.data.get('responder_id')
        notes = request.data.get('notes', 'Dispatched by C2 Desk Officer')

        if not responder_id:
            return api_response(success=False, message="Responder ID required", http_code=status.HTTP_400_BAD_REQUEST)

        responder = get_object_or_404(ResponderUnit, id=responder_id)

        dist = haversine_distance(sos.latitude, sos.longitude, responder.current_latitude, responder.current_longitude)
        if dist > 50.0:
            eta = 6  # Baseline urban response time when cross-city unit assigned
        else:
            eta = max(2, min(25, int(dist * 2.2 + 1)))

        dispatch, created = SOSDispatch.objects.get_or_create(
            sos=sos,
            responder=responder,
            defaults={
                'eta_minutes': eta,
                'dispatch_status': 'ASSIGNED',
                'notes': notes
            }
        )
        if not created:
            dispatch.eta_minutes = eta
            dispatch.dispatch_status = 'ASSIGNED'
            dispatch.notes = notes
            dispatch.dispatched_at = timezone.now()
            dispatch.save(update_fields=['eta_minutes', 'dispatch_status', 'notes', 'dispatched_at'])

        responder.status = 'DISPATCHED'
        responder.save(update_fields=['status'])

        sos.status = 'RESPONDING'
        sos.save(update_fields=['status'])

        # Broadcast update
        channel_layer = get_channel_layer()
        if channel_layer:
            payload = {
                "type": "sos_responder_dispatched",
                "sos_id": sos.sos_id,
                "status": "RESPONDING",
                "responder": ResponderUnitSerializer(responder).data,
                "eta_minutes": eta,
                "notes": notes
            }
            async_to_sync(channel_layer.group_send)(
                f"sos_beacon_{sos.sos_id}",
                {"type": "sos_channel_message", "data": payload}
            )
            async_to_sync(channel_layer.group_send)(
                "c2_operations_feed",
                {"type": "c2_broadcast_event", "data": payload}
            )

        return api_response(success=True, message=f"Unit {responder.callsign} dispatched to scene", data=SOSDispatchSerializer(dispatch).data)


class MarkOnSceneSOSAPIView(APIView):
    """Authority C2 operator marks responder unit arrived on scene."""
    permission_classes = [IsAuthority]

    def post(self, request, sos_id):
        sos = get_object_or_404(SOSAlert, sos_id=sos_id)
        notes = request.data.get('notes', 'Responder unit arrived on scene.')

        sos.status = 'RESPONDING'
        sos.save(update_fields=['status'])

        for dispatch in sos.dispatches.all():
            dispatch.dispatch_status = 'ARRIVED'
            dispatch.arrived_at = timezone.now()
            dispatch.notes += f" | {notes}"
            dispatch.save(update_fields=['dispatch_status', 'arrived_at', 'notes'])

            responder = dispatch.responder
            responder.status = 'ON_SCENE'
            responder.save(update_fields=['status'])

        channel_layer = get_channel_layer()
        if channel_layer:
            payload = {
                "type": "sos_status_change",
                "sos_id": sos.sos_id,
                "status": "ON_SCENE",
                "notes": notes,
                "timestamp": timezone.now().isoformat()
            }
            async_to_sync(channel_layer.group_send)(
                f"sos_beacon_{sos.sos_id}",
                {"type": "sos_channel_message", "data": payload}
            )
            async_to_sync(channel_layer.group_send)(
                "c2_operations_feed",
                {"type": "c2_broadcast_event", "data": payload}
            )

        return api_response(success=True, message=f"Emergency {sos.sos_id} marked ON SCENE", data=SOSAlertSerializer(sos).data)


class ResolveSOSAPIView(APIView):
    """Authority C2 operator or responder resolves an emergency upon securing the tourist."""
    permission_classes = [IsAuthority]

    def post(self, request, sos_id):
        sos = get_object_or_404(SOSAlert, sos_id=sos_id)
        resolution_notes = request.data.get('notes', 'Tourist secured and confirmed safe by responder team.')

        sos.status = 'RESOLVED'
        sos.resolved_at = timezone.now()
        sos.emergency_notes += f"\n[Resolution]: {resolution_notes}"
        sos.save(update_fields=['status', 'resolved_at', 'emergency_notes'])

        # Reset tourist status
        tourist = sos.tourist
        tourist.trip_status = 'ACTIVE'
        tourist.save(update_fields=['trip_status'])

        # Free up responders
        for dispatch in sos.dispatches.all():
            dispatch.dispatch_status = 'COMPLETED'
            dispatch.save(update_fields=['dispatch_status'])
            responder = dispatch.responder
            responder.status = 'AVAILABLE'
            responder.save(update_fields=['status'])

        # Broadcast update
        channel_layer = get_channel_layer()
        if channel_layer:
            payload = {
                "type": "sos_status_change",
                "sos_id": sos.sos_id,
                "status": "RESOLVED",
                "notes": resolution_notes
            }
            async_to_sync(channel_layer.group_send)(
                f"sos_beacon_{sos.sos_id}",
                {"type": "sos_channel_message", "data": payload}
            )
            async_to_sync(channel_layer.group_send)(
                "c2_operations_feed",
                {"type": "c2_broadcast_event", "data": payload}
            )

        return api_response(success=True, message="SOS Emergency marked RESOLVED and safe.", data=SOSAlertSerializer(sos).data)


class CancelSOSAPIView(APIView):
    """Cancels active SOS (e.g. false alarm or user reported safe)."""
    permission_classes = [AllowAny]

    def post(self, request, sos_id):
        sos = get_object_or_404(SOSAlert, sos_id=sos_id)
        reason = request.data.get('reason', 'User reported safe / accidental trigger')

        sos.status = 'CANCELLED'
        sos.cancellation_reason = reason
        sos.resolved_at = timezone.now()
        sos.save(update_fields=['status', 'cancellation_reason', 'resolved_at'])

        # Reset tourist status
        tourist = sos.tourist
        tourist.trip_status = 'ACTIVE'
        tourist.save(update_fields=['trip_status'])

        # Free up responders
        for dispatch in sos.dispatches.all():
            dispatch.dispatch_status = 'COMPLETED'
            dispatch.notes += f" | Cancelled: {reason}"
            dispatch.save(update_fields=['dispatch_status', 'notes'])
            responder = dispatch.responder
            responder.status = 'AVAILABLE'
            responder.save(update_fields=['status'])

        # Broadcast update
        channel_layer = get_channel_layer()
        if channel_layer:
            payload = {
                "type": "sos_status_change",
                "sos_id": sos.sos_id,
                "status": "CANCELLED",
                "reason": reason
            }
            async_to_sync(channel_layer.group_send)(
                f"sos_beacon_{sos.sos_id}",
                {"type": "sos_channel_message", "data": payload}
            )
            async_to_sync(channel_layer.group_send)(
                "c2_operations_feed",
                {"type": "c2_broadcast_event", "data": payload}
            )

        return api_response(success=True, message="SOS cancelled and marked safe", data=SOSAlertSerializer(sos).data)


class ActiveSOSListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        active_alerts = SOSAlert.objects.filter(status__in=['ACTIVE', 'ACKNOWLEDGED', 'RESPONDING']).order_by('-triggered_at')
        responders = ResponderUnit.objects.all()
        return api_response(success=True, data={
            'sos_alerts': SOSAlertSerializer(active_alerts, many=True).data,
            'responders': ResponderUnitSerializer(responders, many=True).data
        })


class ResponderFleetListCreateAPIView(APIView):
    """
    API to list all PCR vans and register new responder units.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        agency = request.query_params.get('agency')
        status_filter = request.query_params.get('status')
        queryset = ResponderUnit.objects.all().order_by('unit_code')
        if agency:
            queryset = queryset.filter(agency=agency)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return api_response(success=True, data=ResponderUnitSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = ResponderUnitSerializer(data=request.data)
        if serializer.is_valid():
            unit = serializer.save()

            # Broadcast new unit to C2 Operations Room
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    "c2_operations_feed",
                    {
                        "type": "c2_broadcast_event",
                        "data": {
                            "type": "responder_registered",
                            "responder": ResponderUnitSerializer(unit).data
                        }
                    }
                )
            return api_response(
                success=True,
                message=f"PCR Unit {unit.callsign} registered successfully",
                data=ResponderUnitSerializer(unit).data,
                http_code=status.HTTP_201_CREATED
            )
        return api_response(success=False, message="Validation error", errors=serializer.errors, http_code=status.HTTP_400_BAD_REQUEST)


class ResponderDetailUpdateAPIView(APIView):
    """
    API to retrieve, update, or decommission a responder unit.
    """
    permission_classes = [IsAuthority]

    def get(self, request, unit_id):
        unit = get_object_or_404(ResponderUnit, id=unit_id)
        return api_response(success=True, data=ResponderUnitSerializer(unit).data)

    def patch(self, request, unit_id):
        unit = get_object_or_404(ResponderUnit, id=unit_id)
        serializer = ResponderUnitSerializer(unit, data=request.data, partial=True)
        if serializer.is_valid():
            updated_unit = serializer.save()
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    "c2_operations_feed",
                    {
                        "type": "c2_broadcast_event",
                        "data": {
                            "type": "responder_updated",
                            "responder": ResponderUnitSerializer(updated_unit).data
                        }
                    }
                )
            return api_response(success=True, message="PCR Unit updated", data=ResponderUnitSerializer(updated_unit).data)
        return api_response(success=False, errors=serializer.errors, http_code=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, unit_id):
        unit = get_object_or_404(ResponderUnit, id=unit_id)
        callsign = unit.callsign
        unit.delete()
        return api_response(success=True, message=f"PCR Unit {callsign} decommissioned from fleet.")


class ResponderLiveLocationAPIView(APIView):
    """
    Live GPS Telemetry Update for a PCR Van / Responder Unit.
    Updates coordinates, status, and broadcasts real-time position to all C2 screens.
    """
    permission_classes = [IsAuthority]

    def post(self, request, unit_id):
        unit = get_object_or_404(ResponderUnit, id=unit_id)
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        new_status = request.data.get('status')

        if lat is not None and lng is not None:
            unit.current_latitude = float(lat)
            unit.current_longitude = float(lng)

        if new_status and new_status in dict(ResponderUnit.STATUS_CHOICES):
            unit.status = new_status

        unit.last_heartbeat = timezone.now()
        unit.save(update_fields=['current_latitude', 'current_longitude', 'status', 'last_heartbeat'])

        # Broadcast live GPS position over Channels
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "c2_operations_feed",
                {
                    "type": "c2_broadcast_event",
                    "data": {
                        "type": "responder_location_updated",
                        "responder_id": unit.id,
                        "unit_code": unit.unit_code,
                        "callsign": unit.callsign,
                        "agency": unit.agency,
                        "latitude": unit.current_latitude,
                        "longitude": unit.current_longitude,
                        "status": unit.status,
                        "status_display": unit.get_status_display(),
                        "last_heartbeat": unit.last_heartbeat.isoformat()
                    }
                }
            )

        return api_response(
            success=True,
            message=f"Live coordinates updated for {unit.callsign}",
            data=ResponderUnitSerializer(unit).data
        )
