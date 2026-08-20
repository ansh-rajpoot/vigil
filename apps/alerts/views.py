from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from common.utils import api_response
from .models import EmergencyBroadcast, AlertReceipt
from .serializers import EmergencyBroadcastSerializer, AlertReceiptSerializer
from geofencing.models import GeoZone
from tourists.models import TouristProfile
from accounts.permissions import authority_required, IsAuthority


@authority_required
def broadcast_c2_view(request):
    """
    Authority C2 Regional Emergency Broadcast Control Room.
    Dispatches targeted alerts (Disaster, Severe Weather, Crime, Crowd Emergency, etc.)
    with geographic zone targeting and expiration control.
    """
    if request.method == 'POST':
        alert_type = request.POST.get('alert_type', 'GENERAL_SAFETY')
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        severity = request.POST.get('severity', 'WARNING')
        target_type = request.POST.get('target_type', 'ALL_TOURISTS')
        target_zone_id = request.POST.get('target_zone')
        hours_valid = int(request.POST.get('hours_valid', 24))

        zone = GeoZone.objects.filter(id=target_zone_id).first() if target_zone_id else None

        broadcast = EmergencyBroadcast.objects.create(
            alert_type=alert_type,
            title=title,
            message=message,
            severity=severity,
            target_type=target_type,
            target_zone=zone,
            issued_by=request.user,
            is_active=True,
            starts_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(hours=hours_valid)
        )

        # Broadcast live over Django Channels WebSockets
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    "c2_operations_feed",
                    {
                        "type": "c2_broadcast_event",
                        "data": {
                            "type": "disaster_alert",
                            "broadcast": EmergencyBroadcastSerializer(broadcast).data,
                            "timestamp": timezone.now().isoformat()
                        }
                    }
                )
        except Exception as e:
            print(f"WebSocket broadcast error: {e}")

        messages.success(request, f"Emergency broadcast '{broadcast.broadcast_code}' dispatched to all target devices.")
        return redirect('alerts:broadcast_c2')

    now = timezone.now()
    broadcasts = EmergencyBroadcast.objects.filter(is_active=True, expires_at__gte=now).order_by('-created_at')
    zones = GeoZone.objects.filter(is_active=True)

    return render(request, 'authority/broadcast.html', {
        'broadcasts': broadcasts,
        'zones': zones,
        'alert_types': EmergencyBroadcast.ALERT_TYPE_CHOICES,
        'severities': EmergencyBroadcast.SEVERITY_CHOICES,
        'target_types': EmergencyBroadcast.TARGET_TYPE_CHOICES,
    })


# ==============================================================================
# REST API Endpoints
# ==============================================================================

class BroadcastListCreateAPIView(APIView):
    """
    List active non-expired broadcasts or issue a new broadcast.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        now = timezone.now()
        active_only = request.query_params.get('active', 'true') == 'true'

        if active_only:
            queryset = EmergencyBroadcast.objects.filter(is_active=True, starts_at__lte=now, expires_at__gte=now)
        else:
            queryset = EmergencyBroadcast.objects.all()

        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')

        if lat is not None and lng is not None:
            lat = float(lat)
            lng = float(lng)
            filtered = [b for b in queryset if b.applies_to_location(lat, lng)]
            serializer = EmergencyBroadcastSerializer(filtered, many=True)
        else:
            serializer = EmergencyBroadcastSerializer(queryset, many=True)

        return api_response(success=True, data=serializer.data)

    def post(self, request):
        if not request.user.is_authenticated or not (request.user.is_operator or request.user.is_staff):
            return api_response(success=False, message="Operator authorization required", http_code=status.HTTP_403_FORBIDDEN)

        serializer = EmergencyBroadcastSerializer(data=request.data)
        if serializer.is_valid():
            broadcast = serializer.save(issued_by=request.user)

            try:
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        "c2_operations_feed",
                        {
                            "type": "c2_broadcast_event",
                            "data": {
                                "type": "disaster_alert",
                                "broadcast": EmergencyBroadcastSerializer(broadcast).data,
                                "timestamp": timezone.now().isoformat()
                            }
                        }
                    )
            except Exception as e:
                print(f"Broadcast WS error: {e}")

            return api_response(success=True, message="Broadcast dispatched successfully", data=EmergencyBroadcastSerializer(broadcast).data, http_code=status.HTTP_201_CREATED)
        return api_response(success=False, message="Validation error", errors=serializer.errors, http_code=status.HTTP_400_BAD_REQUEST)


class AcknowledgeAlertAPIView(APIView):
    """Tourist acknowledges receipt of an emergency broadcast."""
    permission_classes = [IsAuthenticated]

    def post(self, request, broadcast_code):
        broadcast = get_object_or_404(EmergencyBroadcast, broadcast_code=broadcast_code)
        profile = getattr(request.user, 'tourist_profile', None)

        if not profile:
            return api_response(success=False, message="Tourist profile required", http_code=status.HTTP_400_BAD_REQUEST)

        receipt, _ = AlertReceipt.objects.get_or_create(broadcast=broadcast, tourist=profile)
        receipt.acknowledged_at = timezone.now()
        receipt.save(update_fields=['acknowledged_at'])

        return api_response(success=True, message="Alert acknowledged", data=AlertReceiptSerializer(receipt).data)
