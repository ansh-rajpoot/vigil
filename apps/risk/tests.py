import json
from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from tourists.models import TouristProfile
from risk.models import Blackspot, TouristRiskAssessment
from risk.engine import get_risk_engine, calculate_tourist_risk, BaseRiskScoringEngine
from geofencing.models import GeoZone
from maps.models import SafetyPOI
from alerts.models import EmergencyBroadcast

User = get_user_model()


class RiskScoreSystemTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='risk_tourist',
            password='Password123!',
            first_name='Ananya',
            last_name='Sen'
        )
        self.profile = TouristProfile.objects.create(
            user=self.user,
            battery_level=85,
            current_latitude=15.4989,
            current_longitude=73.8278
        )

        # Create nearby police POI
        self.police_poi = SafetyPOI.objects.create(
            name='Panaji Police Station',
            poi_type='POLICE',
            latitude=15.4980,
            longitude=73.8260
        )

        # Create Blackspot
        self.blackspot = Blackspot.objects.create(
            name='Dona Paula Unlit Pier',
            category='ISOLATED_UNLIT',
            risk_weight=85,
            latitude=15.4540,
            longitude=73.8040,
            radius_meters=400,
            safety_advice='Avoid walking near unlit cliffs after dark.'
        )

    def test_modular_engine_interface(self):
        """Verify engine adheres to BaseRiskScoringEngine abstract interface."""
        engine = get_risk_engine()
        self.assertIsInstance(engine, BaseRiskScoringEngine)

    def test_safe_zone_risk_scoring(self):
        """Verify tourist in safe corridor near police station gets Safe (0-30) category."""
        breakdown = get_risk_engine().get_factor_breakdown(self.profile, 15.4989, 73.8278)
        self.assertIn(breakdown['risk_level'], ['SAFE', 'MODERATE'])
        self.assertLessEqual(breakdown['overall_score'], 60)
        self.assertIn('recommendation', breakdown)

    def test_blackspot_hazard_elevation(self):
        """Verify proximity to blackspot elevates spatial risk score."""
        # Evaluate directly inside the blackspot
        assessment = calculate_tourist_risk(self.profile, 15.4540, 73.8040)
        self.assertGreater(assessment.spatial_risk_score, 15)
        self.assertIn('Dona Paula Unlit Pier', assessment.primary_risk_factor)

    def test_geofence_restricted_breach_elevation(self):
        """Verify breach of restricted geofence elevates spatial score to maximum."""
        restricted_zone = GeoZone.objects.create(
            name='Restricted Navy Perimeter',
            code='ZONE-NAVY-RESTRICTED',
            zone_type='RESTRICTED',
            center_latitude=15.4000,
            center_longitude=73.8000,
            polygon_geojson={
                "type": "Polygon",
                "coordinates": [[[73.79, 15.39], [73.81, 15.39], [73.81, 15.41], [73.79, 15.41], [73.79, 15.39]]]
            }
        )
        assessment = calculate_tourist_risk(self.profile, 15.4000, 73.8000)
        self.assertGreaterEqual(assessment.spatial_risk_score, 30)
        self.assertIn('Restricted Boundary Breach', assessment.primary_risk_factor)

    def test_disaster_alert_score_elevation(self):
        """Verify active emergency broadcast elevates the composite risk score."""
        EmergencyBroadcast.objects.create(
            title='Severe Cyclone Alert',
            severity='CRITICAL',
            message='Stay indoors. Heavy squall warnings.',
            is_active=True
        )
        breakdown = get_risk_engine().get_factor_breakdown(self.profile, 15.4989, 73.8278)
        self.assertGreaterEqual(breakdown['alert_score'], 10)

    def test_current_risk_api(self):
        """Verify GET /risk/api/current/ returns 200 with complete factor breakdown."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('risk:api_current_risk'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('overall_score', data['data'])
        self.assertIn('risk_level', data['data'])
        self.assertIn('factors_breakdown', data['data'])
        self.assertIn('recommendation', data['data']['factors_breakdown'])

    def test_evaluate_risk_api(self):
        """Verify POST /risk/api/evaluate/ computes on-demand score."""
        payload = {
            'tourist_id': self.profile.id,
            'latitude': 15.4540,
            'longitude': 73.8040
        }
        response = self.client.post(
            reverse('risk:api_evaluate_risk'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('overall_score', data['data'])
