from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from tourists.models import TouristProfile
from digital_id.models import DigitalTouristID
from accounts.models import EmergencyContact

User = get_user_model()


class AuthenticationAndRBACркаTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Tourist Account
        self.tourist = User.objects.create_user(
            username='test_tourist',
            email='tourist@test.com',
            password='ValidPassword123!',
            first_name='Ananya',
            last_name='Sen',
            role='TOURIST',
            phone_number='+91 98765 11111',
            is_verified=True
        )
        self.profile = TouristProfile.objects.create(
            user=self.tourist,
            nationality='Indian',
            blood_group='O+'
        )

        # 2. Authority Account (C2 Operator / Police)
        self.authority = User.objects.create_user(
            username='test_authority',
            email='officer@police.gov.in',
            password='ValidPassword123!',
            first_name='Rajesh',
            last_name='Sharma',
            role='OPERATOR',
            agency_name='Goa Police',
            badge_number='GP-101',
            is_verified=True,
            is_staff=False,
            is_superuser=False
        )

        # 3. Tourism Administrator Account
        self.admin_user = User.objects.create_user(
            username='test_admin',
            email='admin@tourism.gov.in',
            password='ValidPassword123!',
            first_name='Sunil',
            last_name='Deshmukh',
            role='ADMIN',
            agency_name='Department of Tourism',
            is_verified=True,
            is_staff=True,
            is_superuser=True
        )

    def test_tourist_login_successful(self):
        """Verify tourist can authenticate and is redirected to tourist dashboard."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'test_tourist',
            'password': 'ValidPassword123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('tourists:home'))

    def test_authority_login_successful(self):
        """Verify authority officer can authenticate and is redirected to C2 tactical map."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'test_authority',
            'password': 'ValidPassword123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard:c2_command'))

    def test_administrator_login_successful(self):
        """Verify tourism administrator can authenticate and is redirected to central admin portal."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'test_admin',
            'password': 'ValidPassword123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:admin_portal'))

    def test_invalid_credentials_denied(self):
        """Verify invalid passwords or non-existent usernames fail authentication."""
        # Wrong password
        response = self.client.post(reverse('accounts:login'), {
            'username': 'test_tourist',
            'password': 'WrongPassword999!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

        # Non-existent user
        response = self.client.post(reverse('accounts:login'), {
            'username': 'non_existent_user',
            'password': 'SomePassword123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_tourist_cannot_access_authority_c2(self):
        """Strict RBAC: Authenticated Tourist MUST NOT access Authority C2 console (403 Forbidden)."""
        self.client.force_login(self.tourist)
        response = self.client.get(reverse('dashboard:c2_command'))
        self.assertEqual(response.status_code, 403)

    def test_tourist_cannot_access_admin_portal(self):
        """Strict RBAC: Authenticated Tourist MUST NOT access Tourism Admin Portal (403 Forbidden)."""
        self.client.force_login(self.tourist)
        response = self.client.get(reverse('accounts:admin_portal'))
        self.assertEqual(response.status_code, 403)

    def test_authority_cannot_access_admin_portal(self):
        """Strict RBAC: Authenticated Authority MUST NOT access Tourism Admin Portal (403 Forbidden)."""
        self.client.force_login(self.authority)
        response = self.client.get(reverse('accounts:admin_portal'))
        self.assertEqual(response.status_code, 403)

    def test_administrator_can_access_admin_portal_and_c2(self):
        """Administrator has access to both admin portal and C2 console."""
        self.client.force_login(self.admin_user)
        response_admin = self.client.get(reverse('accounts:admin_portal'))
        self.assertEqual(response_admin.status_code, 200)

        response_c2 = self.client.get(reverse('dashboard:c2_command'))
        self.assertEqual(response_c2.status_code, 200)

    def test_anonymous_redirected_to_login(self):
        """Unauthenticated requests to protected endpoints redirect to login."""
        self.client.logout()

        res_tourist = self.client.get(reverse('tourists:home'))
        self.assertEqual(res_tourist.status_code, 302)
        self.assertIn('/auth/login/', res_tourist.url)

        res_c2 = self.client.get(reverse('dashboard:c2_command'))
        self.assertEqual(res_c2.status_code, 302)
        self.assertIn('/auth/login/', res_c2.url)

        res_admin = self.client.get(reverse('accounts:admin_portal'))
        self.assertEqual(res_admin.status_code, 302)
        self.assertIn('/auth/login/', res_admin.url)

    def test_tourist_registration(self):
        """Verify tourist self-registration generates user, profile, and digital tourist ID."""
        reg_payload = {
            'username': 'new_tourist_emma',
            'first_name': 'Emma',
            'last_name': 'Watson',
            'email': 'emma.watson@example.com',
            'phone_number': '+91 98222 33445',
            'password1': 'StrongPass2026!',
            'password2': 'StrongPass2026!',
            'nationality': 'British',
            'blood_group': 'A+',
            'hotel_stay_details': 'W Goa, Vagator',
            'emergency_contact_name': 'Robert Watson',
            'emergency_contact_phone': '+44 7700 900077',
            'emergency_contact_relation': 'Father'
        }
        response = self.client.post(reverse('accounts:register'), reg_payload)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('tourists:home'))

        created_user = User.objects.get(username='new_tourist_emma')
        self.assertEqual(created_user.role, 'TOURIST')
        self.assertTrue(hasattr(created_user, 'tourist_profile'))
        self.assertTrue(hasattr(created_user.tourist_profile, 'digital_id'))
        self.assertEqual(created_user.emergency_contacts.count(), 1)

    def test_profile_management_updates(self):
        """Verify user can update profile information, add and remove emergency contacts."""
        self.client.force_login(self.tourist)

        # 1. Update personal details
        response = self.client.post(reverse('accounts:profile_management'), {
            'action': 'update_profile',
            'first_name': 'Ananya (Updated)',
            'last_name': 'Sen',
            'email': 'ananya.updated@test.com',
            'phone_number': '+91 98765 99999'
        })
        self.assertEqual(response.status_code, 302)
        self.tourist.refresh_from_db()
        self.assertEqual(self.tourist.first_name, 'Ananya (Updated)')

        # 2. Add emergency contact
        response = self.client.post(reverse('accounts:profile_management'), {
            'action': 'add_contact',
            'name': 'Priya Sen',
            'relationship': 'Sister',
            'phone_number': '+91 98765 88888',
            'email': 'priya@test.com',
            'is_primary': True
        })
        self.assertEqual(response.status_code, 302)
        contact = EmergencyContact.objects.get(user=self.tourist, name='Priya Sen')
        self.assertEqual(contact.relationship, 'Sister')

        # 3. Delete emergency contact
        response = self.client.post(reverse('accounts:profile_management'), {
            'action': 'delete_contact',
            'contact_id': contact.id
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(EmergencyContact.objects.filter(id=contact.id).exists())

    def test_logout(self):
        """Verify logout flushes session."""
        self.client.force_login(self.tourist)
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:login'))

    def test_admin_rest_api_role_change(self):
        """Verify DRF API role updates are restricted to Tourism Administrators."""
        # 1. Tourist attempt -> 403
        self.client.force_login(self.tourist)
        res = self.client.patch(f"/auth/api/admin/users/{self.tourist.id}/", {'role': 'ADMIN'}, content_type='application/json')
        self.assertEqual(res.status_code, 403)

        # 2. Admin attempt -> 200 OK
        self.client.force_login(self.admin_user)
        res = self.client.patch(f"/auth/api/admin/users/{self.tourist.id}/", {'role': 'AUTHORITY'}, content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.tourist.refresh_from_db()
        self.assertEqual(self.tourist.role, 'AUTHORITY')
