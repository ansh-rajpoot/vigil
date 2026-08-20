import json
from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from tourists.models import TouristProfile
from digital_id.models import DigitalTouristID, IDVerificationLog
from common.utils import verify_dynamic_totp_token

User = get_user_model()


class DigitalIDSystemTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='ananya_sen',
            password='Password123!',
            first_name='Ananya',
            last_name='Sen',
            email='ananya@example.com',
            phone_number='+91 98765 43210'
        )
        self.profile = TouristProfile.objects.create(
            user=self.user,
            nationality='Indian',
            blood_group='O+',
            destination_city='Goa',
            hotel_stay_details='Taj Fort Aguada Resort'
        )
        self.digital_id = DigitalTouristID.objects.create(
            tourist=self.profile,
            id_number='VGL-2026-T89Q2',
            crypto_hash='crypto_signature_hash_987',
            status='ACTIVE',
            valid_until=timezone.now() + timezone.timedelta(days=14),
            verification_token_secret='sih_secret_key_2026_ananya'
        )
        self.digital_id.generate_qr_code()

    def test_unique_id_and_token_rotation(self):
        """Verify dynamic TOTP generates a 6-digit numeric token that rotates every 30s."""
        totp = self.digital_id.get_current_totp()
        self.assertEqual(len(totp), 6)
        self.assertTrue(totp.isdigit())
        self.assertTrue(verify_dynamic_totp_token(self.digital_id.verification_token_secret, totp, step=30, window=1))

    def test_qr_payload_privacy_safety(self):
        """Ensure QR code payload contains only verification identifiers, NOT sensitive unencrypted data."""
        payload = self.digital_id.get_qr_payload_dict()
        self.assertEqual(payload['v_id'], 'VGL-2026-T89Q2')
        self.assertIn('totp', payload)
        self.assertIn('sig', payload)
        self.assertIn('verify_url', payload)
        # Ensure sensitive unencrypted fields are NOT exposed directly in the QR string
        self.assertNotIn('password', payload)
        self.assertNotIn('phone_number', payload)

    def test_qr_code_image_generation(self):
        """Verify PNG QR code file is generated and attached to model."""
        self.assertTrue(bool(self.digital_id.qr_code_image))
        self.assertTrue(self.digital_id.qr_code_image.name.startswith('qr_codes/qr_VGL-2026-T89Q2'))

    def test_verify_api_genuine_id(self):
        """Verify checkpoint API validates genuine ID and returns verified KYC metadata."""
        payload = self.digital_id.get_qr_payload_dict()
        response = self.client.post('/digital-id/api/verify/', {
            'id_number': self.digital_id.id_number,
            'totp_code': payload['totp'],
            'verifier_name': 'Inspector V. Naik',
            'location_name': 'Calangute North Checkpoint'
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['verification_result'], 'VALID')
        self.assertEqual(data['data']['tourist_name'], 'Ananya Sen')
        self.assertEqual(data['data']['blood_group'], 'O+')
        self.assertTrue(data['data']['token_verified'])

        # Verify audit log was created
        log = IDVerificationLog.objects.filter(digital_id=self.digital_id).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status_result, 'VALID')
        self.assertEqual(log.verifier_name, 'Inspector V. Naik')

    def test_verify_api_invalid_nonexistent_id(self):
        """Verify non-existent ID returns 404 with INVALID_ID result."""
        response = self.client.post('/digital-id/api/verify/', {
            'id_number': 'VGL-FAKE-99999',
            'verifier_name': 'Officer Test'
        }, content_type='application/json')

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['data']['verification_result'], 'INVALID_ID')

    def test_verify_api_expired_id(self):
        """Verify expired ID returns EXPIRED status."""
        self.digital_id.valid_until = timezone.now() - timezone.timedelta(days=1)
        self.digital_id.save()

        response = self.client.post('/digital-id/api/verify/', {
            'id_number': self.digital_id.id_number
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['data']['verification_result'], 'EXPIRED')

    def test_verify_api_flagged_id(self):
        """Verify flagged / security watchlist ID returns FLAGGED_ALERT status."""
        self.digital_id.status = 'FLAGGED'
        self.digital_id.save()

        response = self.client.post('/digital-id/api/verify/', {
            'id_number': self.digital_id.id_number
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['data']['verification_result'], 'FLAGGED_ALERT')

    def test_dynamic_qr_refresh_api(self):
        """Verify authenticated tourist can refresh their dynamic QR payload."""
        self.client.force_login(self.user)
        response = self.client.get('/digital-id/api/dynamic-qr/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['id_number'], 'VGL-2026-T89Q2')
        self.assertIn('totp', data['data'])
        self.assertLessEqual(data['data']['expires_in_seconds'], 30)

    def test_public_verify_page_rendering(self):
        """Verify checkpoint scanner HTML portal loads cleanly."""
        response = self.client.get(reverse('digital_id:verify_portal'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Digital Tourist ID Scanner")
        self.assertContains(response, "Live QR Scanner")
