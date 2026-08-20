import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from tourists.models import TouristProfile
from incidents.models import Incident, IncidentTimeline
from emergency.models import ResponderUnit

User = get_user_model()


class IncidentReportingTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Tourist User
        self.tourist_user = User.objects.create_user(
            username='reporting_tourist',
            password='Password123!',
            first_name='Ananya',
            last_name='Sen',
            phone_number='+91 98765 43210'
        )
        self.profile = TouristProfile.objects.create(
            user=self.tourist_user,
            current_latitude=15.4989,
            current_longitude=73.8278
        )

        # 2. Authority Operator
        self.operator_user = User.objects.create_user(
            username='operator_sharma',
            password='Password123!',
            role='OPERATOR',
            badge_number='GOA-POL-8821'
        )

        # 3. Responder Unit
        self.pcr_unit = ResponderUnit.objects.create(
            unit_code='PCR-CALANGUTE-01',
            agency='TOURISM_POLICE',
            callsign='Patrol Unit Calangute 01',
            officer_in_charge='Sub-Inspector Patil',
            contact_number='+91 94220 11004',
            status='AVAILABLE',
            current_latitude=15.5420,
            current_longitude=73.7580
        )

    def test_tourist_file_incident_report(self):
        """Verify tourist can submit incident report with category, location, and severity."""
        self.client.force_login(self.tourist_user)

        # Small valid dummy PNG image
        image_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
        evidence_file = SimpleUploadedFile("evidence.png", image_content, content_type="image/png")

        data = {
            'category': 'HARASSMENT',
            'title': 'Tout aggressive harassment near beach shack',
            'description': 'Two unauthorized individuals persistently demanding money.',
            'location_name': 'Baga Beach Shack #4',
            'severity': 'HIGH',
            'latitude': 15.5520,
            'longitude': 73.7540,
            'evidence_image': evidence_file
        }

        response = self.client.post(reverse('incidents:tourist_report'), data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify DB record
        incident = Incident.objects.filter(reporter=self.tourist_user).first()
        self.assertIsNotNone(incident)
        self.assertEqual(incident.category, 'HARASSMENT')
        self.assertEqual(incident.severity, 'HIGH')
        self.assertEqual(incident.status, 'REPORTED')
        self.assertEqual(incident.location_name, 'Baga Beach Shack #4')
        self.assertTrue(bool(incident.evidence_image))

        # Verify timeline log
        self.assertEqual(incident.timeline.count(), 1)
        self.assertEqual(incident.timeline.first().status, 'REPORTED')

    def test_authority_filter_and_status_progression(self):
        """Verify authority can filter incidents and progress status from REPORTED to VERIFIED to RESOLVED."""
        incident = Incident.objects.create(
            reporter=self.tourist_user,
            reporter_name='Ananya Sen',
            category='CRIME',
            severity='HIGH',
            status='REPORTED',
            title='Bag snatching at Calangute market',
            description='Scooter rider snatched handbag.',
            latitude=15.5420,
            longitude=73.7580
        )

        self.client.force_login(self.operator_user)

        # 1. Filter by category
        res_filter = self.client.get(reverse('incidents:api_incidents') + '?category=CRIME&status=REPORTED')
        self.assertEqual(res_filter.status_code, 200)
        self.assertEqual(len(res_filter.json()['data']), 1)

        # 2. Update to VERIFIED
        res_verify = self.client.patch(
            reverse('incidents:api_incident_detail', kwargs={'incident_id': incident.incident_id}),
            data=json.dumps({'status': 'VERIFIED', 'timeline_note': 'C2 verified with CCTV camera 04'}),
            content_type='application/json'
        )
        self.assertEqual(res_verify.status_code, 200)
        incident.refresh_from_db()
        self.assertEqual(incident.status, 'VERIFIED')

        # 3. Assign Responder Unit
        res_assign = self.client.patch(
            reverse('incidents:api_incident_detail', kwargs={'incident_id': incident.incident_id}),
            data=json.dumps({'assigned_responder_id': self.pcr_unit.id}),
            content_type='application/json'
        )
        self.assertEqual(res_assign.status_code, 200)
        incident.refresh_from_db()
        self.assertEqual(incident.status, 'ASSIGNED')
        self.assertEqual(incident.assigned_responder, self.pcr_unit)

        # 4. Resolve Incident
        res_resolve = self.client.patch(
            reverse('incidents:api_incident_detail', kwargs={'incident_id': incident.incident_id}),
            data=json.dumps({'status': 'RESOLVED', 'resolution_notes': 'Suspect apprehended by SI Patil. Property recovered.'}),
            content_type='application/json'
        )
        self.assertEqual(res_resolve.status_code, 200)
        incident.refresh_from_db()
        self.assertEqual(incident.status, 'RESOLVED')
        self.assertIsNotNone(incident.resolved_at)
        self.assertIn('Property recovered', incident.resolution_notes)

    def test_incident_categories_and_map_presence(self):
        """Verify all categories are valid and returned in GIS map layer endpoint."""
        for cat in ['ACCIDENT', 'CRIME', 'HARASSMENT', 'MEDICAL', 'LOST_PERSON', 'LOST_PROPERTY', 'NATURAL_DISASTER', 'UNSAFE_AREA', 'OTHER']:
            Incident.objects.create(
                category=cat,
                title=f"Sample {cat} incident",
                description="Test description",
                latitude=15.4989,
                longitude=73.8278,
                status='REPORTED'
            )

        response = self.client.get(reverse('maps:api_gis_layers'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['data']['incidents']), 9)

    def test_public_incidents_feed_and_detail_views(self):
        """Verify public community incidents feed and detail views render correctly."""
        inc = Incident.objects.create(
            reporter=self.tourist_user,
            reporter_name='Ananya Sen',
            category='UNSAFE_AREA',
            severity='MEDIUM',
            status='REPORTED',
            title='Unlit alleyway near beach',
            description='Streetlights are out for 300 meters.',
            location_name='Anjuna Cliff Alley',
            latitude=15.5800,
            longitude=73.7400
        )

        # 1. Anonymous / Public Feed
        res_feed = self.client.get(reverse('incidents:incident_feed'))
        self.assertEqual(res_feed.status_code, 200)
        self.assertContains(res_feed, 'Unlit alleyway near beach')
        self.assertContains(res_feed, 'Anjuna Cliff Alley')

        # 2. Filtered Feed
        res_filtered = self.client.get(reverse('incidents:incident_feed') + '?category=UNSAFE_AREA')
        self.assertEqual(res_filtered.status_code, 200)
        self.assertContains(res_filtered, 'Unlit alleyway near beach')

        # 3. Incident Detail View
        res_detail = self.client.get(reverse('incidents:incident_detail', kwargs={'incident_id': inc.incident_id}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, inc.incident_id)
        self.assertContains(res_detail, 'Streetlights are out for 300 meters')
