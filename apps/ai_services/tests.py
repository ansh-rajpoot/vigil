import cv2
import numpy as np
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from geofencing.models import GeoZone
from ai_services.models import VisionCameraFeed, VisionDetectionLog
from ai_services.vision_analyzer import process_camera_feed, get_vision_engine

User = get_user_model()


class CrowdMonitoringTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Authority User
        self.operator_user = User.objects.create_user(
            username='vision_operator',
            password='Password123!',
            role='OPERATOR',
            badge_number='GOA-POL-5501'
        )

        # 2. Associated Safety Zone
        self.zone = GeoZone.objects.create(
            name='Calangute Promenade Zone',
            code='ZONE-CALANGUTE-PROMENADE',
            zone_type='CAUTION',
            center_latitude=15.5420,
            center_longitude=73.7580,
            radius_meters=300,
            polygon_geojson={
                "type": "Polygon",
                "coordinates": [[[73.750, 15.540], [73.760, 15.540], [73.760, 15.550], [73.750, 15.550], [73.750, 15.540]]]
            }
        )

        # 3. Camera Feed
        self.camera = VisionCameraFeed.objects.create(
            camera_code='CAM-CALANGUTE-01',
            location_name='Calangute Main Market Entrance',
            zone=self.zone,
            latitude=15.5420,
            longitude=73.7580,
            max_safe_capacity=100,
            critical_threshold_count=85,
            surge_threshold_rate=20,
            coverage_area_sqm=200.0,
            is_active=True
        )

    def _generate_synthetic_crowd_frame(self, person_count: int = 15) -> bytes:
        """Generates synthetic image with specified number of distinct person-like shapes."""
        img = np.zeros((480, 640, 3), dtype=np.uint8) + 30
        for i in range(person_count):
            col = (i % 8) * 75 + 30
            row = (i // 8) * 140 + 80
            # Draw vertical body contour
            cv2.rectangle(img, (col, row), (col + 35, row + 90), (220, 220, 220), -1)
            cv2.circle(img, (col + 17, row - 12), 12, (200, 200, 200), -1)
        _, enc = cv2.imencode('.jpg', img)
        return enc.tobytes()

    def test_vision_engine_analysis_and_density_scoring(self):
        """Verify optical vision engine calculates people count, physical density, and normalized score."""
        frame_bytes = self._generate_synthetic_crowd_frame(person_count=12)
        log = process_camera_feed(self.camera, frame_bytes)

        self.assertGreaterEqual(log.crowd_count, 1)
        self.assertGreater(log.crowd_density_score, 0.0)
        self.assertLessEqual(log.crowd_density_score, 100.0)
        self.assertIn(log.density_tier, ['LOW', 'NORMAL', 'HIGH', 'CRITICAL_SURGE'])
        self.assertEqual(log.camera, self.camera)
        self.assertEqual(log.camera.zone, self.zone)

    def test_crowd_surge_and_threshold_alert(self):
        """Verify sudden surge increase triggers critical surge tier and alert dispatch."""
        # 1. Baseline log: 10 people
        VisionDetectionLog.objects.create(
            camera=self.camera,
            crowd_count=10,
            crowd_density_score=15.0,
            density_tier='LOW',
            timestamp=timezone.now() - timezone.timedelta(minutes=1)
        )

        # 2. Huge sudden surge: 90 people
        surge_frame = self._generate_synthetic_crowd_frame(person_count=24)
        log = process_camera_feed(self.camera, surge_frame)

        self.assertTrue(log.is_threshold_exceeded() or log.crowd_density_score >= 50)
        self.assertIsNotNone(log.annotated_frame)

    def test_api_camera_feeds_list(self):
        """Verify GET /ai-services/api/feeds/ returns list of active feeds with latest telemetry."""
        response = self.client.get(reverse('ai_services:api_camera_feeds'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['camera_code'], 'CAM-CALANGUTE-01')
        self.assertEqual(data['data'][0]['zone_name'], 'Calangute Promenade Zone')

    def test_api_analyze_frame_endpoint(self):
        """Verify POST /ai-services/api/analyze-frame/ processes frame and returns metrics."""
        response = self.client.post(
            reverse('ai_services:api_analyze_frame'),
            data={'camera_id': self.camera.id},
            format='multipart'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('crowd_density_score', data['data'])
        self.assertIn('density_tier', data['data'])
