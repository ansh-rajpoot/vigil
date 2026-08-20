import json
from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from channels.testing import WebsocketCommunicator
from tourists.models import TouristProfile
from emergency.models import SOSAlert, ResponderUnit, SOSDispatch, SOSLiveBreadcrumb
from digital_id.models import DigitalTouristID
from emergency.consumers import C2OperationsConsumer, SOSBeaconConsumer, TouristAlertConsumer

User = get_user_model()


class IntelligentSOSTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Create Tourist with Digital ID
        self.tourist_user = User.objects.create_user(
            username='sos_tourist',
            password='Password123!',
            first_name='Ananya',
            last_name='Sen',
            phone_number='+91 98765 43210'
        )
        self.profile = TouristProfile.objects.create(
            user=self.tourist_user,
            nationality='Indian',
            blood_group='O+',
            current_latitude=15.4989,
            current_longitude=73.8278,
            battery_level=88
        )
        self.digital_id = DigitalTouristID.objects.create(
            tourist=self.profile,
            id_number='VGL-2026-T89Q2',
            crypto_hash='hash_abc_123',
            valid_until=timezone.now() + timezone.timedelta(days=30),
            verification_token_secret='secret_ananya_key'
        )

        # 2. Create Authority Operator
        self.operator_user = User.objects.create_user(
            username='operator_sharma',
            password='Password123!',
            role='OPERATOR',
            badge_number='GOA-POL-8821'
        )

        # 3. Create Responder Units
        self.pcr_unit = ResponderUnit.objects.create(
            unit_code='PCR-PANJIM-01',
            agency='POLICE',
            callsign='Patrol Alpha PCR-01',
            officer_in_charge='Head Constable S. Naik',
            contact_number='+91 94220 11001',
            status='AVAILABLE',
            current_latitude=15.4950,
            current_longitude=73.8240,
            station_base_name='Panaji Police HQ'
        )
        self.ems_unit = ResponderUnit.objects.create(
            unit_code='108-EMS-02',
            agency='AMBULANCE',
            callsign='108 EMS Ambulance 02',
            officer_in_charge='Paramedic D. Fernandes',
            contact_number='+91 94220 10802',
            status='AVAILABLE',
            current_latitude=15.5100,
            current_longitude=73.8150
        )

    def test_complete_sos_trigger_and_auto_dispatch(self):
        """Verify SOS activation captures location, links digital ID, and auto-dispatches nearest unit."""
        self.client.force_login(self.tourist_user)

        payload = {
            'latitude': 15.4989,
            'longitude': 73.8278,
            'battery_level': 85,
            'emergency_notes': 'Suspicious individuals following on unlit trail.'
        }
        response = self.client.post(
            reverse('emergency:api_trigger_sos'),
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])

        sos_data = data['data']
        self.assertTrue(sos_data['sos_id'].startswith('SOS-'))
        self.assertEqual(sos_data['tourist_name'], 'Ananya Sen')
        self.assertEqual(sos_data['digital_id_number'], 'VGL-2026-T89Q2')
        self.assertEqual(sos_data['blood_group'], 'O+')

        # Verify DB Record
        sos = SOSAlert.objects.get(sos_id=sos_data['sos_id'])
        self.assertEqual(sos.tourist, self.profile)
        self.assertIn(sos.status, ['ACTIVE', 'RESPONDING'])

        # Verify nearest unit (PCR Patrol Alpha) was auto-dispatched
        self.assertEqual(sos.dispatches.count(), 1)
        dispatch = sos.dispatches.first()
        self.assertEqual(dispatch.responder, self.pcr_unit)

        # Verify responder unit status became DISPATCHED
        self.pcr_unit.refresh_from_db()
        self.assertEqual(self.pcr_unit.status, 'DISPATCHED')

        # Verify tourist status became SOS_ACTIVE
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.trip_status, 'SOS_ACTIVE')

    def test_secondary_sos_updates_active_emergency(self):
        """Verify calling trigger API a 2nd time updates active SOS telemetry without duplicate tickets."""
        self.client.force_login(self.tourist_user)

        # 1st Trigger
        res1 = self.client.post(
            reverse('emergency:api_trigger_sos'),
            data=json.dumps({'latitude': 15.4989, 'longitude': 73.8278}),
            content_type='application/json'
        )
        self.assertEqual(res1.status_code, 201)
        sos_id_1 = res1.json()['data']['sos_id']
        self.assertEqual(SOSAlert.objects.filter(tourist=self.profile).count(), 1)

        # 2nd Trigger (Update position during active emergency)
        res2 = self.client.post(
            reverse('emergency:api_trigger_sos'),
            data=json.dumps({'latitude': 15.5000, 'longitude': 73.8300, 'emergency_notes': 'Updated location'}),
            content_type='application/json'
        )
        self.assertEqual(res2.status_code, 200)
        sos_id_2 = res2.json()['data']['sos_id']

        # Ensure same SOS record is updated without creating duplicate popups/records
        self.assertEqual(sos_id_1, sos_id_2)
        self.assertEqual(SOSAlert.objects.filter(tourist=self.profile).count(), 1)

        # Verify coordinates updated
        sos = SOSAlert.objects.get(sos_id=sos_id_1)
        self.assertEqual(sos.latitude, 15.5000)
        self.assertEqual(sos.longitude, 73.8300)

    def test_authority_acknowledgement(self):
        """Verify C2 operator can acknowledge active SOS."""
        sos = SOSAlert.objects.create(
            tourist=self.profile,
            status='ACTIVE',
            latitude=15.4989,
            longitude=73.8278
        )

        self.client.force_login(self.operator_user)
        response = self.client.post(
            reverse('emergency:api_acknowledge_sos', kwargs={'sos_id': sos.sos_id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        sos.refresh_from_db()
        self.assertEqual(sos.status, 'ACKNOWLEDGED')
        self.assertIsNotNone(sos.acknowledged_at)

    def test_authority_response_dispatch(self):
        """Verify C2 operator can manually assign additional responder units."""
        sos = SOSAlert.objects.create(
            tourist=self.profile,
            status='ACKNOWLEDGED',
            latitude=15.4989,
            longitude=73.8278
        )

        self.client.force_login(self.operator_user)
        response = self.client.post(
            reverse('emergency:api_respond_sos', kwargs={'sos_id': sos.sos_id}),
            data=json.dumps({
                'responder_id': self.ems_unit.id,
                'notes': '108 Ambulance dispatched for medical precaution.'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        sos.refresh_from_db()
        self.assertEqual(sos.status, 'RESPONDING')

        self.ems_unit.refresh_from_db()
        self.assertEqual(self.ems_unit.status, 'DISPATCHED')

    def test_resolve_emergency_and_free_responders(self):
        """Verify resolving emergency resets tourist status to ACTIVE and frees responders."""
        sos = SOSAlert.objects.create(
            tourist=self.profile,
            status='RESPONDING',
            latitude=15.4989,
            longitude=73.8278
        )
        SOSDispatch.objects.create(
            sos=sos,
            responder=self.pcr_unit,
            dispatch_status='ARRIVED'
        )
        self.pcr_unit.status = 'DISPATCHED'
        self.pcr_unit.save()

        self.client.force_login(self.operator_user)
        response = self.client.post(
            reverse('emergency:api_resolve_sos', kwargs={'sos_id': sos.sos_id}),
            data=json.dumps({'notes': 'Tourist escorted to hotel lobby safely.'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        sos.refresh_from_db()
        self.assertEqual(sos.status, 'RESOLVED')
        self.assertIsNotNone(sos.resolved_at)

        # Tourist status reset
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.trip_status, 'ACTIVE')

        # Responder freed back to AVAILABLE
        self.pcr_unit.refresh_from_db()
        self.assertEqual(self.pcr_unit.status, 'AVAILABLE')

    def test_cancel_false_alarm_sos(self):
        """Verify tourist can cancel accidental trigger and reset status."""
        sos = SOSAlert.objects.create(
            tourist=self.profile,
            status='ACTIVE',
            latitude=15.4989,
            longitude=73.8278
        )

        response = self.client.post(
            reverse('emergency:api_cancel_sos', kwargs={'sos_id': sos.sos_id}),
            data=json.dumps({'reason': 'Accidental tap by child'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        sos.refresh_from_db()
        self.assertEqual(sos.status, 'CANCELLED')
        self.assertEqual(sos.cancellation_reason, 'Accidental tap by child')

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.trip_status, 'ACTIVE')

    def test_fleet_manager_view_and_registration(self):
        """Verify authority can access fleet portal and register new PCR vans."""
        self.client.force_login(self.operator_user)

        # 1. Access Fleet Manager page
        res_view = self.client.get(reverse('emergency:fleet_manager'))
        self.assertEqual(res_view.status_code, 200)
        self.assertContains(res_view, 'Patrol Alpha PCR-01')

        # 2. Register New PCR Van
        payload = {
            'unit_code': 'PCR-CALANGUTE-03',
            'agency': 'POLICE',
            'callsign': 'Patrol Unit Calangute 03',
            'officer_in_charge': 'Sub-Inspector R. Naik',
            'contact_number': '+91 98221 00112',
            'station_base_name': 'Calangute Coastal Post',
            'current_latitude': 15.5420,
            'current_longitude': 73.7580,
            'status': 'AVAILABLE'
        }
        res_reg = self.client.post(
            reverse('emergency:api_responders'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res_reg.status_code, 201)
        data = res_reg.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['unit_code'], 'PCR-CALANGUTE-03')

        # Verify in DB
        new_unit = ResponderUnit.objects.filter(unit_code='PCR-CALANGUTE-03').first()
        self.assertIsNotNone(new_unit)
        self.assertEqual(new_unit.callsign, 'Patrol Unit Calangute 03')

    def test_responder_live_location_telemetry(self):
        """Verify PCR van live GPS location update API works and broadcasts telemetry."""
        self.client.force_login(self.operator_user)

        payload = {
            'latitude': 15.5560,
            'longitude': 73.7530,
            'status': 'ON_SCENE'
        }
        res_loc = self.client.post(
            reverse('emergency:api_responder_location', kwargs={'unit_id': self.pcr_unit.id}),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res_loc.status_code, 200)
        data = res_loc.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['current_latitude'], 15.5560)
        self.assertEqual(data['data']['current_longitude'], 73.7530)
        self.assertEqual(data['data']['status'], 'ON_SCENE')

        self.pcr_unit.refresh_from_db()
        self.assertEqual(self.pcr_unit.current_latitude, 15.5560)
        self.assertEqual(self.pcr_unit.status, 'ON_SCENE')


class ChannelsWebsocketTestCase(TransactionTestCase):
    def setUp(self):
        self.operator_user = User.objects.create_user(
            username='ws_operator',
            password='Password123!',
            role='OPERATOR',
            badge_number='GOA-POL-7711'
        )
        self.tourist_user = User.objects.create_user(
            username='ws_tourist',
            password='Password123!',
            role='TOURIST'
        )

    async def test_c2_websocket_authorized_operator(self):
        """Verify operator with authority credentials successfully connects to C2 telemetry feed."""
        communicator = WebsocketCommunicator(C2OperationsConsumer.as_asgi(), "/ws/c2/telemetry/")
        communicator.scope['user'] = self.operator_user

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        # Receive connection established message
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'connection_established')
        self.assertEqual(response['officer'], 'ws_operator')

        await communicator.disconnect()

    async def test_c2_websocket_unauthorized_tourist_rejected(self):
        """Verify non-authority tourist user connection to C2 feed is rejected with code 4003."""
        communicator = WebsocketCommunicator(C2OperationsConsumer.as_asgi(), "/ws/c2/telemetry/")
        communicator.scope['user'] = self.tourist_user

        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4003)
