import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from tourists.models import TouristProfile
from emergency.models import SOSAlert, ResponderUnit
from incidents.models import Incident
from risk.models import TouristRiskAssessment

User = get_user_model()


class AuthorityDashboardTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Authority Operator
        self.operator_user = User.objects.create_user(
            username='c2_operator',
            password='Password123!',
            role='OPERATOR',
            badge_number='GOA-POL-9901'
        )

        # 2. Tourist User
        self.tourist_user = User.objects.create_user(
            username='tourist_ananya',
            password='Password123!',
            role='TOURIST'
        )
        self.profile = TouristProfile.objects.create(
            user=self.tourist_user,
            current_latitude=15.4989,
            current_longitude=73.8278,
            trip_status='ACTIVE'
        )

        # 3. Seed Incident & SOS
        self.incident = Incident.objects.create(
            category='CRIME',
            severity='HIGH',
            title='Sample Snatching Incident',
            description='Test description',
            location_name='Panaji Promenade',
            latitude=15.4989,
            longitude=73.8278,
            status='REPORTED'
        )
        self.sos = SOSAlert.objects.create(
            tourist=self.profile,
            status='ACTIVE',
            latitude=15.4989,
            longitude=73.8278
        )

    def test_c2_dashboard_rendered_for_authority(self):
        """Verify authority operator can load C2 Command Center with top metrics and map canvas."""
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('dashboard:c2_command'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "c2-tactical-map")
        self.assertContains(response, "Active Monitored Tourists")
        self.assertContains(response, "Active SOS Panic Alerts")

    def test_c2_dashboard_forbidden_for_tourist(self):
        """Verify non-authority tourist is blocked with 403 Forbidden."""
        self.client.force_login(self.tourist_user)
        response = self.client.get(reverse('dashboard:c2_command'))
        self.assertEqual(response.status_code, 403)

    def test_c2_telemetry_api(self):
        """Verify GET /dashboard/api/c2/telemetry/ returns aggregated real-time data."""
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('dashboard:api_c2_telemetry'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('metrics', data['data'])
        self.assertIn('sos_alerts', data['data'])
        self.assertIn('responders', data['data'])

    def test_analytics_dashboard_view(self):
        """Verify dedicated analytics console loads with Chart.js canvases and KPIs."""
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('dashboard:analytics_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "chart-incident-timeline")
        self.assertContains(response, "chart-incident-category")
        self.assertContains(response, "chart-incident-severity")
        self.assertContains(response, "chart-incident-location")
        self.assertContains(response, "chart-risk-distribution")

    def test_analytics_api_filters_and_data_integrity(self):
        """Verify analytics API returns database-aggregated metrics across today, 7d, 30d, and custom ranges."""
        self.client.force_login(self.operator_user)

        # 1. 7-Day Filter
        res_7d = self.client.get(reverse('dashboard:api_analytics') + '?range=7d')
        self.assertEqual(res_7d.status_code, 200)
        data_7d = res_7d.json()['data']
        self.assertEqual(data_7d['time_range'], '7d')
        self.assertIn('charts', data_7d)
        self.assertIn('categories', data_7d['charts'])
        self.assertIn('severities', data_7d['charts'])
        self.assertIn('locations', data_7d['charts'])
        self.assertIn('risk_distribution', data_7d['charts'])

        # 2. Today Filter
        res_today = self.client.get(reverse('dashboard:api_analytics') + '?range=today')
        self.assertEqual(res_today.status_code, 200)
        data_today = res_today.json()['data']
        self.assertEqual(data_today['time_range'], 'today')

        # 3. 30-Day Filter
        res_30d = self.client.get(reverse('dashboard:api_analytics') + '?range=30d')
        self.assertEqual(res_30d.status_code, 200)
        data_30d = res_30d.json()['data']
        self.assertEqual(data_30d['time_range'], '30d')

        # 4. Custom Date Range
        start = (timezone.now() - timedelta(days=14)).strftime('%Y-%m-%d')
        end = timezone.now().strftime('%Y-%m-%d')
        res_custom = self.client.get(f"{reverse('dashboard:api_analytics')}?range=custom&start_date={start}&end_date={end}")
        self.assertEqual(res_custom.status_code, 200)
        data_custom = res_custom.json()['data']
        self.assertEqual(data_custom['time_range'], 'custom')
