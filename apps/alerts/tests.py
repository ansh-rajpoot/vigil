import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from geofencing.models import GeoZone
from tourists.models import TouristProfile
from alerts.models import EmergencyBroadcast, AlertReceipt

User = get_user_model()


class AlertSystemTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Authority Operator
        self.operator_user = User.objects.create_user(
            username='alert_operator',
            password='Password123!',
            role='OPERATOR',
            badge_number='GOA-POL-3301'
        )

        # 2. Tourist User
        self.tourist_user = User.objects.create_user(
            username='alert_tourist',
            password='Password123!',
            role='TOURIST'
        )
        self.profile = TouristProfile.objects.create(
            user=self.tourist_user,
            current_latitude=15.5420,
            current_longitude=73.7580
        )

        # 3. Geographic Zone (Calangute Beach)
        self.zone = GeoZone.objects.create(
            name='Calangute Coast',
            code='ZONE-CALANGUTE-COAST',
            zone_type='CAUTION',
            center_latitude=15.5420,
            center_longitude=73.7580,
            radius_meters=400,
            polygon_geojson={
                "type": "Polygon",
                "coordinates": [[[73.750, 15.540], [73.760, 15.540], [73.760, 15.550], [73.750, 15.550], [73.750, 15.540]]]
            }
        )

    def test_authority_create_broadcast_api(self):
        """Verify authority can dispatch emergency broadcasts across alert types."""
        self.client.force_login(self.operator_user)

        payload = {
            'alert_type': 'SEVERE_WEATHER',
            'title': 'High Wave Hazard - North Goa',
            'message': 'Immediate advisory: Wave height exceeding 3.5m. Stay 50m back from shoreline.',
            'severity': 'WARNING',
            'target_type': 'ZONE_SPECIFIC',
            'target_zone': self.zone.id,
            'hours_valid': 12
        }

        response = self.client.post(
            reverse('alerts:api_broadcasts'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])

        broadcast_code = data['data']['broadcast_code']
        broadcast = EmergencyBroadcast.objects.get(broadcast_code=broadcast_code)
        self.assertEqual(broadcast.alert_type, 'SEVERE_WEATHER')
        self.assertEqual(broadcast.severity, 'WARNING')
        self.assertEqual(broadcast.target_zone, self.zone)
        self.assertTrue(broadcast.is_currently_active())

    def test_geographic_targeting_for_tourists(self):
        """Verify alert targeted to a specific zone only applies to tourists within that zone."""
        broadcast = EmergencyBroadcast.objects.create(
            alert_type='DISASTER',
            title='Flash Surge Evacuation',
            message='Evacuate low-lying sand bars immediately.',
            severity='CRITICAL',
            target_type='ZONE_SPECIFIC',
            target_zone=self.zone,
            issued_by=self.operator_user
        )

        # 1. Tourist inside zone (15.5420, 73.7580)
        self.assertTrue(broadcast.applies_to_location(15.5420, 73.7580))

        # 2. Tourist outside zone (Panaji: 15.4989, 73.8278)
        self.assertFalse(broadcast.applies_to_location(15.4989, 73.8278))

    def test_alert_expiry_filtering(self):
        """Verify expired broadcasts are marked inactive and filtered from active APIs."""
        # Active Broadcast
        active_alert = EmergencyBroadcast.objects.create(
            alert_type='CRIME_ACTIVITY',
            title='Night Security Advisory',
            message='Police foot patrols active.',
            severity='ADVISORY',
            starts_at=timezone.now() - timezone.timedelta(hours=1),
            expires_at=timezone.now() + timezone.timedelta(hours=5)
        )
        self.assertTrue(active_alert.is_currently_active())

        # Expired Broadcast
        expired_alert = EmergencyBroadcast.objects.create(
            alert_type='ACCIDENT',
            title='Road Blockage Cleared',
            message='Old traffic detour.',
            severity='WARNING',
            starts_at=timezone.now() - timezone.timedelta(hours=10),
            expires_at=timezone.now() - timezone.timedelta(hours=1)
        )
        self.assertFalse(expired_alert.is_currently_active())

        # API check
        response = self.client.get(reverse('alerts:api_broadcasts') + '?active=true')
        self.assertEqual(response.status_code, 200)
        active_codes = [b['broadcast_code'] for b in response.json()['data']]
        self.assertIn(active_alert.broadcast_code, active_codes)
        self.assertNotIn(expired_alert.broadcast_code, active_codes)

    def test_tourist_acknowledge_alert(self):
        """Verify tourist can acknowledge receipt of an active alert."""
        broadcast = EmergencyBroadcast.objects.create(
            alert_type='GENERAL_SAFETY',
            title='Tourist Safety Notice',
            message='Keep emergency contacts updated.',
            severity='ADVISORY'
        )

        self.client.force_login(self.tourist_user)
        response = self.client.post(
            reverse('alerts:api_acknowledge_alert', kwargs={'broadcast_code': broadcast.broadcast_code}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AlertReceipt.objects.filter(broadcast=broadcast, tourist=self.profile).count(), 1)
        receipt = AlertReceipt.objects.get(broadcast=broadcast, tourist=self.profile)
        self.assertIsNotNone(receipt.acknowledged_at)
