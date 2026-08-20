import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from tourists.models import TouristProfile
from geofencing.models import GeoZone, TouristZonePresence, GeofenceBreachLog
from geofencing.engine import process_tourist_geofence_transitions

User = get_user_model()


class SmartGeofencingTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Tourist
        self.tourist_user = User.objects.create_user(
            username='geofence_tourist',
            password='Password123!',
            first_name='Ananya',
            last_name='Sen'
        )
        self.profile = TouristProfile.objects.create(
            user=self.tourist_user,
            battery_level=90,
            current_latitude=15.4989,
            current_longitude=73.8278
        )

        # Create Operator
        self.operator_user = User.objects.create_user(
            username='operator_sharma',
            password='Password123!',
            role='OPERATOR'
        )

        # 1. Safe Haven Zone
        self.safe_zone = GeoZone.objects.create(
            name='Panaji Promenade Safe Haven',
            code='ZONE-SAFE-01',
            zone_type='SAFE',
            center_latitude=15.4989,
            center_longitude=73.8278,
            radius_meters=400,
            polygon_geojson={
                "type": "Polygon",
                "coordinates": [[[73.820, 15.490], [73.835, 15.490], [73.835, 15.505], [73.820, 15.505], [73.820, 15.490]]]
            },
            safety_advisory='Monitored by Panaji CCTV and Tourist Assistance Desk.'
        )

        # 2. Restricted Zone
        self.restricted_zone = GeoZone.objects.create(
            name='Fort Aguada Cliff Restricted Area',
            code='ZONE-RESTRICTED-01',
            zone_type='RESTRICTED',
            center_latitude=15.5900,
            center_longitude=73.7400,
            radius_meters=300,
            polygon_geojson={
                "type": "Polygon",
                "coordinates": [[[73.735, 15.585], [73.745, 15.585], [73.745, 15.595], [73.735, 15.595], [73.735, 15.585]]]
            },
            safety_advisory='Treacherous slip hazard and falling rocks. No civilian access.'
        )

        # 3. High Risk Zone
        self.high_risk_zone = GeoZone.objects.create(
            name='Vagator Rip Current Danger Sector',
            code='ZONE-HIGHRISK-01',
            zone_type='HIGH_RISK',
            center_latitude=15.6000,
            center_longitude=73.7300,
            radius_meters=350,
            polygon_geojson={
                "type": "Polygon",
                "coordinates": [[[73.725, 15.595], [73.735, 15.595], [73.735, 15.605], [73.725, 15.605], [73.725, 15.595]]]
            },
            safety_advisory='High surf and dangerous undertow. Swimming prohibited.'
        )

    def test_entering_safe_zone(self):
        """Verify tourist entering safe zone creates presence and logs entry without authority alarm."""
        result = process_tourist_geofence_transitions(self.profile, 15.4989, 73.8278)
        self.assertTrue(result['is_in_any_zone'])
        self.assertEqual(result['newly_entered_count'], 1)
        self.assertEqual(len(result['authority_alerts_dispatched']), 0)

        # Verify active presence
        presence = TouristZonePresence.objects.filter(tourist=self.profile, zone=self.safe_zone, is_active=True).first()
        self.assertIsNotNone(presence)

        # Verify log
        log = GeofenceBreachLog.objects.filter(tourist=self.profile, zone=self.safe_zone).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.breach_type, 'ENTRY_SAFE')
        self.assertFalse(log.authority_notified)

    def test_entering_restricted_zone(self):
        """Verify entering restricted zone updates risk score and alerts authorities."""
        result = process_tourist_geofence_transitions(self.profile, 15.5900, 73.7400)
        self.assertTrue(result['is_in_any_zone'])
        self.assertEqual(result['newly_entered_count'], 1)
        self.assertEqual(len(result['authority_alerts_dispatched']), 1)

        # Verify breach log
        log = GeofenceBreachLog.objects.filter(tourist=self.profile, zone=self.restricted_zone).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.breach_type, 'ENTER_RESTRICTED')
        self.assertTrue(log.authority_notified)
        self.assertGreaterEqual(log.risk_score_after, 30)

    def test_duplicate_alert_prevention_when_remaining_inside(self):
        """Verify subsequent heartbeats within the same zone suppress duplicate alerts."""
        # 1st heartbeat -> generates alert
        res1 = process_tourist_geofence_transitions(self.profile, 15.5900, 73.7400)
        self.assertEqual(res1['newly_entered_count'], 1)
        self.assertEqual(GeofenceBreachLog.objects.filter(tourist=self.profile, zone=self.restricted_zone).count(), 1)

        # 2nd heartbeat at same/nearby location within zone -> NO duplicate alert
        res2 = process_tourist_geofence_transitions(self.profile, 15.5901, 73.7401)
        self.assertEqual(res2['newly_entered_count'], 0)
        self.assertEqual(res2['persisting_zone_count'], 1)
        self.assertEqual(len(res2['new_alerts']), 0)
        # Breach log count remains 1
        self.assertEqual(GeofenceBreachLog.objects.filter(tourist=self.profile, zone=self.restricted_zone).count(), 1)

    def test_leaving_zone_detection(self):
        """Verify moving outside the zone marks presence inactive and logs exit event."""
        # Enter zone
        process_tourist_geofence_transitions(self.profile, 15.5900, 73.7400)
        self.assertTrue(TouristZonePresence.objects.filter(tourist=self.profile, is_active=True).exists())

        # Move outside to neutral location (Panaji outskirts: 15.45, 73.90)
        res_exit = process_tourist_geofence_transitions(self.profile, 15.4500, 73.9000)
        self.assertEqual(res_exit['exited_count'], 1)
        self.assertFalse(TouristZonePresence.objects.filter(tourist=self.profile, is_active=True).exists())

        # Exit breach log recorded
        exit_log = GeofenceBreachLog.objects.filter(tourist=self.profile, breach_type='ZONE_EXIT').first()
        self.assertIsNotNone(exit_log)

    def test_authority_create_geozone_api(self):
        """Verify authority operator can create a new geofence zone via REST API."""
        self.client.force_login(self.operator_user)
        payload = {
            'name': 'Baga Beach Curfew Zone',
            'code': 'ZONE-BAGA-CURFEW-01',
            'zone_type': 'CAUTION',
            'center_latitude': 15.5500,
            'center_longitude': 73.7500,
            'radius_meters': 500,
            'polygon_geojson': {
                "type": "Polygon",
                "coordinates": [[[73.745, 15.545], [73.755, 15.545], [73.755, 15.555], [73.745, 15.555], [73.745, 15.545]]]
            },
            'safety_advisory': 'Curfew in effect from 23:00 to 05:00.'
        }
        response = self.client.post(
            reverse('geofencing:api_zones'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['name'], 'Baga Beach Curfew Zone')
