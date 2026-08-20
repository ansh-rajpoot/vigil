from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from demo.scenario_engine import reset_to_demo_baseline, execute_demo_step
from tourists.models import TouristProfile
from emergency.models import SOSAlert, ResponderUnit

User = get_user_model()


class ControlledDemoTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        reset_to_demo_baseline()

    def test_demo_baseline_seeding(self):
        """Verify baseline reset creates all necessary tourists, geofences, and responders."""
        tourist_count = TouristProfile.objects.count()
        self.assertGreaterEqual(tourist_count, 5)

        p1 = TouristProfile.objects.filter(user__username='tourist_ananya').first()
        self.assertIsNotNone(p1)
        self.assertEqual(p1.trip_status, 'ACTIVE')

        available_units = ResponderUnit.objects.filter(status='AVAILABLE').count()
        self.assertGreaterEqual(available_units, 3)

    def test_full_12_step_demo_execution(self):
        """Verify all 12 steps of the controlled SIH demonstration flow execute sequentially."""
        for step in range(1, 13):
            result = execute_demo_step(step)
            self.assertEqual(result['step'], step)
            self.assertIn('title', result)
            self.assertIn('description', result)

        # Verify state after step 11 (resolved) and step 12 (analytics)
        p1 = TouristProfile.objects.get(user__username='tourist_ananya')
        self.assertEqual(p1.trip_status, 'ACTIVE')

        sos = SOSAlert.objects.filter(sos_id='SOS-2026-DEMO01').first()
        self.assertIsNotNone(sos)
        self.assertEqual(sos.status, 'RESOLVED')

    def test_demo_rest_apis(self):
        """Verify REST endpoints for reset, step execution, and status inspection."""
        # 1. Status API
        res_status = self.client.get(reverse('demo:api_status'))
        self.assertEqual(res_status.status_code, 200)
        self.assertTrue(res_status.json()['success'])

        # 2. Trigger Step 3 (High-Risk Entry)
        res_step = self.client.post(reverse('demo:api_step', kwargs={'step_id': 3}))
        self.assertEqual(res_step.status_code, 200)
        data = res_step.json()['data']
        self.assertEqual(data['step'], 3)

        # 3. Reset API
        res_reset = self.client.post(reverse('demo:api_reset'))
        self.assertEqual(res_reset.status_code, 200)
        self.assertTrue(res_reset.json()['success'])

    def test_demo_controller_ui_rendered(self):
        """Verify SIH Demonstration Controller view renders with 200 OK."""
        response = self.client.get(reverse('demo:controller'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "VIGIL — SIH DEMONSTRATION CONTROLLER")
        self.assertContains(response, "Tourists Appear on Map")
        self.assertContains(response, "Tourist Triggers SOS")
        self.assertContains(response, "Incident is Resolved")
