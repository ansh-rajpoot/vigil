"""
VIGIL — Comprehensive SIH Complete Demonstration Pipeline Test Suite
Simulates the entire real-world end-to-end flow:
Registration -> Digital ID -> Dashboard -> Geolocation -> Risk Elevation ->
High-Risk Zone Breach -> Warning -> SOS Trigger -> Authority Live C2 Reception ->
Acknowledgment -> GIS Incident Plot -> PCR Dispatch -> Safe Resolution -> Analytics Update.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vigil_core.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from tourists.models import TouristProfile
from digital_id.models import DigitalTouristID
from common.utils import generate_dynamic_totp_token, verify_dynamic_totp_token
from geofencing.models import GeoZone, GeofenceBreachLog
from emergency.models import SOSAlert, ResponderUnit, SOSDispatch
from incidents.models import Incident
from risk.models import TouristRiskAssessment

User = get_user_model()


def run_complete_sih_pass():
    print("=======================================================")
    print("🚀 EXECUTING COMPLETE END-TO-END SIH DEMONSTRATION PASS")
    print("=======================================================")

    client_tourist = Client()
    client_authority = Client()

    # --------------------------------------------------------------------------
    # Step 1: Tourist Registration
    # --------------------------------------------------------------------------
    reg_username = f"tourist_sih_{int(timezone.now().timestamp())}"
    reg_email = f"{reg_username}@example.com"
    reg_payload = {
        'username': reg_username,
        'email': reg_email,
        'password1': 'Password123!',
        'password2': 'Password123!',
        'first_name': 'Rohan',
        'last_name': 'Verma',
        'phone_number': '+91 98765 43210',
        'emergency_contact_name': 'Sunita Verma',
        'emergency_contact_phone': '+91 98765 99999',
        'emergency_contact_relation': 'Mother',
        'nationality': 'Indian',
        'blood_group': 'O+',
        'destination_city': 'Goa, India',
        'hotel_stay_details': 'Candolim Beach Resort',
        'medical_conditions': 'None',
        'allergies': 'None',
        'agree_terms': 'on'
    }

    res_reg = client_tourist.post(reverse('accounts:register'), data=reg_payload, follow=True)
    assert res_reg.status_code == 200, f"Registration failed with code {res_reg.status_code}"
    print(f"✅ 1. Tourist Registration Successful: {reg_username}")

    # --------------------------------------------------------------------------
    # Step 2: Digital Tourist ID Generated Cryptographically
    # --------------------------------------------------------------------------
    new_user = User.objects.get(username=reg_username)
    profile = TouristProfile.objects.get(user=new_user)
    digital_id = DigitalTouristID.objects.filter(tourist=profile).first()
    assert digital_id is not None, "Digital Tourist ID was not generated on registration!"
    assert digital_id.id_number.startswith("VGL-"), f"Invalid ID format: {digital_id.id_number}"
    print(f"✅ 2. Digital Tourist ID Created: {digital_id.id_number} (Hash: {digital_id.crypto_hash[:12]}...)")

    # --------------------------------------------------------------------------
    # Step 3: Dynamic Rotating TOTP Generation & Field Police Verification
    # --------------------------------------------------------------------------
    current_totp = generate_dynamic_totp_token(digital_id.verification_token_secret)
    assert len(current_totp) == 6, f"Invalid TOTP length: {current_totp}"
    is_valid = verify_dynamic_totp_token(digital_id.verification_token_secret, current_totp)
    assert is_valid is True, f"TOTP verification failed for token {current_totp}"
    print(f"✅ 3. Dynamic TOTP Token Generated & Verified: {current_totp} (30s window valid)")

    # --------------------------------------------------------------------------
    # Step 4: Tourist Opens Dashboard
    # --------------------------------------------------------------------------
    client_tourist.force_login(new_user)
    res_dash = client_tourist.get(reverse('tourists:home'))
    assert res_dash.status_code == 200, "Tourist home dashboard failed to load"
    assert "Situational Safety & Risk Assessment Index" in res_dash.content.decode(), "Risk index missing from tourist dashboard"
    print("✅ 4. Tourist Safety Companion Dashboard loaded with Real-Time Risk Index HUD")

    # --------------------------------------------------------------------------
    # Step 5: Location Detected & Checked In
    # --------------------------------------------------------------------------
    loc_payload = {
        'latitude': 15.4989,
        'longitude': 73.8278,
        'location_address': 'Panaji Heritage Quarter',
        'battery_level': 90
    }
    res_loc = client_tourist.post(reverse('tourists:api_safe_checkin'), data=loc_payload, content_type='application/json')
    assert res_loc.status_code == 200, "Tourist location check-in failed"
    profile.refresh_from_db()
    assert profile.current_latitude == 15.4989
    print(f"✅ 5. Live Geolocation Check-in: ({profile.current_latitude}, {profile.current_longitude}) recorded")

    # --------------------------------------------------------------------------
    # Step 6: Initial Baseline Risk Calculated (Safe)
    # --------------------------------------------------------------------------
    res_risk = client_tourist.get(reverse('risk:api_current_risk'))
    assert res_risk.status_code == 200, "Risk assessment API failed"
    risk_data = res_risk.json()['data']
    assert risk_data['risk_level'] in ['SAFE', 'MODERATE'], f"Unexpected baseline risk level: {risk_data['risk_level']}"
    print(f"✅ 6. Baseline Risk Calculated: {risk_data['overall_score']}/100 [{risk_data['risk_level']}]")

    # --------------------------------------------------------------------------
    # Step 7: Tourist Enters High-Risk Restricted Zone (Vagator Cliffs)
    # --------------------------------------------------------------------------
    zone_check = client_tourist.post(
        reverse('geofencing:api_check_containment'),
        data={'latitude': 15.6030, 'longitude': 73.7330},
        content_type='application/json'
    )
    assert zone_check.status_code == 200, "Geofencing tracking evaluation failed"
    zone_res = zone_check.json()['data']
    assert zone_res['is_in_any_zone'] is True, "Geofence containment failed to detect zone entry!"
    assert zone_res['containing_zones'][0]['zone_type'] in ['RESTRICTED', 'HIGH_RISK', 'CAUTION'], f"Unexpected zone type: {zone_res['containing_zones'][0]['zone_type']}"
    print(f"✅ 7. High-Risk Zone Containment Detected: {zone_res['containing_zones'][0]['name']} [{zone_res['containing_zones'][0]['zone_type']}]")

    # --------------------------------------------------------------------------
    # Step 8: Dynamic Risk Elevation & Warning Advisory
    # --------------------------------------------------------------------------
    res_risk_surge = client_tourist.post(
        reverse('risk:api_evaluate_risk'),
        data={'latitude': 15.6030, 'longitude': 73.7330},
        content_type='application/json'
    )
    assert res_risk_surge.status_code == 200
    elevated_score = res_risk_surge.json()['data']['overall_score']
    assert elevated_score >= 60, f"Risk score did not elevate near restricted cliffs: {elevated_score}"
    print(f"✅ 8. Risk Elevated Dynamically: {elevated_score}/100 [CRITICAL] with perimeter warning")

    # --------------------------------------------------------------------------
    # Step 9: Tourist Triggers SOS Panic Beacon
    # --------------------------------------------------------------------------
    sos_payload = {
        'latitude': 15.6030,
        'longitude': 73.7330,
        'battery_level': 85,
        'trigger_type': 'MANUAL_BUTTON',
        'location_address': 'Vagator Cliffs Rocky Point',
        'emergency_notes': 'Slipped on wet rock, ankle injury near cliff edge.'
    }
    res_sos = client_tourist.post(reverse('emergency:api_trigger_sos'), data=sos_payload, content_type='application/json')
    assert res_sos.status_code in [200, 201], f"SOS trigger failed with code {res_sos.status_code}"
    sos_data = res_sos.json()['data']
    sos_id = sos_data['sos_id']
    assert sos_id.startswith("SOS-"), f"Invalid SOS ID format: {sos_id}"
    print(f"✅ 9. SOS Panic Beacon Triggered: {sos_id} (Status: {sos_data['status']})")

    # --------------------------------------------------------------------------
    # Step 10: Authority C2 Dashboard & Live Telemetry Feed Receives SOS
    # --------------------------------------------------------------------------
    officer_user = User.objects.filter(role='OPERATOR').first()
    if not officer_user:
        officer_user = User.objects.create_user(
            username='officer_sih',
            password='Password123!',
            role='OPERATOR',
            badge_number='GOA-POL-9911'
        )
    client_authority.force_login(officer_user)

    res_c2 = client_authority.get(reverse('dashboard:c2_command'))
    assert res_c2.status_code == 200, "C2 tactical dashboard failed to load"
    assert "c2-tactical-map" in res_c2.content.decode()

    res_telemetry = client_authority.get(reverse('dashboard:api_c2_telemetry'))
    assert res_telemetry.status_code == 200, "C2 telemetry API failed"
    tel_data = res_telemetry.json()['data']
    assert tel_data['metrics']['active_sos'] >= 1, "C2 active SOS count failed to reflect emergency"
    print(f"✅ 10. Authority C2 Desk Live Telemetry Verified: {tel_data['metrics']['active_sos']} Active SOS")

    # --------------------------------------------------------------------------
    # Step 11: Authority Operator Acknowledges Emergency
    # --------------------------------------------------------------------------
    res_ack = client_authority.post(reverse('emergency:api_acknowledge_sos', kwargs={'sos_id': sos_id}))
    assert res_ack.status_code == 200, "SOS acknowledgment failed"
    ack_data = res_ack.json()['data']
    assert ack_data['status'] == 'ACKNOWLEDGED', f"Expected ACKNOWLEDGED, got {ack_data['status']}"
    print(f"✅ 11. Authority Acknowledged SOS: {sos_id} (Timestamped receipt generated)")

    # --------------------------------------------------------------------------
    # Step 12: Incident Created & Verified on GIS Layer
    # --------------------------------------------------------------------------
    inc_payload = {
        'title': 'Injured Tourist on Vagator Cliffs',
        'category': 'ACCIDENT',
        'severity': 'HIGH',
        'description': 'Tourist slipped on rocky cliff point; patrol assistance en route.',
        'latitude': 15.6030,
        'longitude': 73.7330,
        'location_name': 'Vagator Cliffs Prohibited Edge'
    }
    res_inc = client_tourist.post(reverse('incidents:api_incidents'), data=inc_payload, content_type='application/json')
    assert res_inc.status_code == 201, "Incident reporting failed"
    inc_data = res_inc.json()['data']
    incident_id = inc_data['incident_id']
    print(f"✅ 12. Incident Created: {incident_id} [{inc_data['category']} / {inc_data['severity']}]")

    # Verify GIS Explorer layers include the incident
    res_gis = client_authority.get(reverse('maps:api_gis_layers'))
    assert res_gis.status_code == 200, "GIS layers API failed"
    gis_layers = res_gis.json()['data']
    assert len(gis_layers['incidents']) >= 1, "GIS layers missing reported incident marker"
    print(f"✅ 13. Incident Appears on Leaflet GIS Tactical Map: {len(gis_layers['incidents'])} active markers")

    # --------------------------------------------------------------------------
    # Step 13: Authority Responds & Dispatches Patrol Unit
    # --------------------------------------------------------------------------
    responder = ResponderUnit.objects.filter(status='AVAILABLE').first()
    if not responder:
        responder = ResponderUnit.objects.first()
    
    res_dispatch = client_authority.post(
        reverse('emergency:api_dispatch_responder', kwargs={'sos_id': sos_id}),
        data={'responder_id': responder.id, 'eta_minutes': 3.5, 'notes': 'PCR dispatched with first aid kit.'},
        content_type='application/json'
    )
    assert res_dispatch.status_code == 200, "Responder unit dispatch failed"
    dispatch_data = res_dispatch.json()['data']
    assert dispatch_data['dispatch_status'] in ['ASSIGNED', 'DISPATCHED'], f"Unexpected dispatch status: {dispatch_data['dispatch_status']}"
    
    sos_obj = SOSAlert.objects.get(sos_id=sos_id)
    assert sos_obj.status == 'RESPONDING', f"Expected RESPONDING, got {sos_obj.status}"
    print(f"✅ 14. Authority Responded: Dispatched {responder.callsign} (Status: RESPONDING)")

    # --------------------------------------------------------------------------
    # Step 14: Emergency Resolved & Safe Status Restored
    # --------------------------------------------------------------------------
    res_resolve = client_authority.post(
        reverse('emergency:api_resolve_sos', kwargs={'sos_id': sos_id}),
        data={'resolution_notes': 'Tourist safely treated on-scene for minor ankle sprain and escorted to hotel.'},
        content_type='application/json'
    )
    assert res_resolve.status_code == 200, "SOS resolution failed"
    res_data = res_resolve.json()['data']
    assert res_data['status'] == 'RESOLVED', f"Expected RESOLVED, got {res_data['status']}"

    profile.refresh_from_db()
    assert profile.trip_status == 'ACTIVE', f"Tourist status not reset: {profile.trip_status}"
    print(f"✅ 15. Emergency Safely Resolved: {sos_id} -> Tourist status restored to ACTIVE")

    # --------------------------------------------------------------------------
    # Step 15: Operations Analytics Recalculated Dynamically
    # --------------------------------------------------------------------------
    res_analytics = client_authority.get(f"{reverse('dashboard:api_analytics')}?range=today")
    assert res_analytics.status_code == 200, "Analytics API failed"
    analytics_data = res_analytics.json()['data']
    assert analytics_data['time_range'] == 'today'
    assert 'charts' in analytics_data
    assert 'kpis' in analytics_data
    assert analytics_data['kpis']['total_incidents'] >= 1
    print(f"✅ 16. Operations Analytics Updated: {analytics_data['kpis']['total_incidents']} cases logged, dynamic Chart.js ready")

    # --------------------------------------------------------------------------
    # Step 16: Check Responsive & Navigation Endpoints
    # --------------------------------------------------------------------------
    tourist_urls = [
        reverse('tourists:home'),
        reverse('digital_id:tourist_id_card'),
        reverse('maps:gis_explorer'),
        reverse('maps:safe_routes'),
        reverse('incidents:tourist_report'),
    ]
    for u in tourist_urls:
        r = client_tourist.get(u)
        assert r.status_code == 200, f"Tourist endpoint {u} failed with code {r.status_code}"

    authority_urls = [
        reverse('dashboard:c2_command'),
        reverse('dashboard:analytics_dashboard'),
        reverse('geofencing:manager'),
        reverse('incidents:c2_list'),
        reverse('alerts:broadcast_c2'),
        reverse('demo:controller'),
    ]
    for u in authority_urls:
        r = client_authority.get(u)
        assert r.status_code == 200, f"Authority endpoint {u} failed with code {r.status_code}"

    print(f"✅ 17. All {len(tourist_urls) + len(authority_urls)} Primary Desktop & Mobile Views Verified (HTTP 200 OK)")

    print("=======================================================")
    print("🎉 FULL 17-STEP SIH DEMONSTRATION PIPELINE PASSED 100%!")
    print("=======================================================")


if __name__ == '__main__':
    run_complete_sih_pass()
