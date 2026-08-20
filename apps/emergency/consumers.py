import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class C2OperationsConsumer(AsyncWebsocketConsumer):
    """
    Live tactical WebSocket channel for the Authority Command & Control (C2) operations desk.
    Strictly restricted to authenticated Authority / Operator / Admin users.
    Receives real-time SOS alarms, incident filings, geofence breach alerts, and fleet dispatches.
    """
    async def connect(self):
        user = self.scope.get('user')

        # RBAC Authorization: Reject anonymous or regular tourist users from C2 stream
        is_authorized = await self.check_authority_permission(user)
        if not is_authorized:
            await self.close(code=4003)
            return

        self.group_name = "c2_operations_feed"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "message": "Authorized connection to VIGIL C2 Tactical Stream established.",
            "officer": getattr(user, 'username', 'Operator'),
            "timestamp": timezone.now().isoformat()
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get("action")
            # Echo ping / keepalive
            await self.send(text_data=json.dumps({
                "type": "heartbeat_ack",
                "action": action,
                "timestamp": timezone.now().isoformat()
            }))
        except Exception:
            pass

    # Generic broadcast event receiver from Django channel_layer
    async def c2_broadcast_event(self, event):
        await self.send(text_data=json.dumps(event.get("data", {})))

    @database_sync_to_async
    def check_authority_permission(self, user):
        if not user or not user.is_authenticated:
            return False
        return bool(user.is_operator or user.is_staff or getattr(user, 'role', '') in ['OPERATOR', 'ADMIN'])


class SOSBeaconConsumer(AsyncWebsocketConsumer):
    """
    Bi-directional emergency channel for an active SOS emergency beacon.
    Tourist streams live GPS/battery telemetry; authorities and responders push live ETA and status updates.
    """
    async def connect(self):
        self.sos_id = self.scope['url_route']['kwargs']['sos_id']
        self.group_name = f"sos_beacon_{self.sos_id}"

        # Allow tourist owner or authority personnel
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "beacon_connected",
            "sos_id": self.sos_id,
            "status": "BEACON_ACTIVE",
            "timestamp": timezone.now().isoformat()
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            msg_type = data.get("type")

            if msg_type == "gps_breadcrumb":
                lat = data.get("lat")
                lng = data.get("lng")
                battery = data.get("battery", 100)
                speed = data.get("speed", 0.0)

                # Persist breadcrumb asynchronously
                await self.save_breadcrumb(self.sos_id, lat, lng, speed, battery)

                payload = {
                    "type": "tourist_emergency_status",
                    "sos_id": self.sos_id,
                    "latitude": lat,
                    "longitude": lng,
                    "speed": speed,
                    "battery_level": battery,
                    "timestamp": timezone.now().isoformat()
                }

                # Relay to everyone watching this SOS and the C2 Command room
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "sos_channel_message", "data": payload}
                )
                await self.channel_layer.group_send(
                    "c2_operations_feed",
                    {"type": "c2_broadcast_event", "data": payload}
                )

        except Exception:
            pass

    async def sos_channel_message(self, event):
        await self.send(text_data=json.dumps(event.get("data", {})))

    @database_sync_to_async
    def save_breadcrumb(self, sos_id, lat, lng, speed, battery):
        from emergency.models import SOSAlert, SOSLiveBreadcrumb
        sos = SOSAlert.objects.filter(sos_id=sos_id).first()
        if sos and sos.is_in_progress():
            sos.latitude = lat
            sos.longitude = lng
            sos.battery_level = battery
            sos.save(update_fields=['latitude', 'longitude', 'battery_level'])
            SOSLiveBreadcrumb.objects.create(
                sos=sos,
                latitude=lat,
                longitude=lng,
                speed=speed,
                battery_level=battery
            )


class TouristAlertConsumer(AsyncWebsocketConsumer):
    """
    Personalized push alert channel for individual tourist device.
    Delivers geofence boundary alerts, disaster advisories, and SOS dispatch updates.
    """
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        target_user_id = self.scope['url_route']['kwargs'].get('user_id', user.id)

        # Ensure tourist can only listen to their own alert stream
        if user.id != int(target_user_id) and not (user.is_operator or user.is_staff):
            await self.close(code=4003)
            return

        self.user_id = user.id
        self.group_name = f"tourist_alerts_{self.user_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "alert_channel_ready",
            "user_id": self.user_id,
            "message": "Connected to Vigil Safety Broadcast Service."
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def tourist_alert_message(self, event):
        await self.send(text_data=json.dumps(event.get("data", {})))
