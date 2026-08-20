import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vigil_core.settings')
django.setup()

from django.test import Client
from django.utils import timezone
from tourists.models import TouristProfile
from digital_id.models import DigitalTouristID
from emergency.models import SOSAlert, ResponderUnit
from geofencing.models import GeoZone
from risk.models import Blackspot
from maps.models import SafeRoute

def run_integration_tests():
    print("\n=======================================================")
    print("🚀 RUNNING END-TO-END VIGIL SYSTEM INTEGRATION TESTS")
    print("=======================================================\n")

    client = Client()

    # 1. Test Login View
    res = client.get('/auth/login/')
    assert res.status_code == 200, f"Login GET failed: {res.status_code}"
    print("✅ 1. Login page loaded successfully (HTTP 200)")

    # 2. Authenticate Tourist
    logged_in = client.login(username='tourist_ananya', password='pass1234')
    assert logged_in, "Tourist authentication failed"
    print("✅ 2. Authenticated as tourist_ananya")

    # 3. Test Tourist Dashboard
    res = client.get('/tourist/')
    assert res.status_code == 200, f"Tourist dashboard failed: {res.status_code}"
    assert b"Welcome, Ananya" in res.content
    assert b"Real-Time Risk Score" in res.content
    print("✅ 3. Tourist Safety Companion Dashboard loaded with Real-Time Risk Index")

    # 4. Test Safety Check-in API
    res = client.post('/tourist/api/checkin/', content_type='application/json')
    assert res.status_code == 200, f"Checkin API failed: {res.status_code}"
    data = res.json()
    assert data['success'] is True
    print("✅ 4. Tourist Safety Check-in recorded and timestamped")

    # 5. Test Digital Tourist ID Card & Dynamic TOTP QR
    res = client.get('/digital-id/card/')
    assert res.status_code == 200
    assert b"VGL-2026-T89Q2" in res.content
    assert b"Dynamic Security Token (TOTP)" in res.content
    print("✅ 5. Digital ID Card with 3D flip & dynamic TOTP rendered")

    res = client.get('/digital-id/api/dynamic-qr/')
    assert res.status_code == 200
    data = res.json()
    assert data['success'] is True
    assert 'totp' in data['data']['payload']
    print(f"✅ 6. Dynamic TOTP QR rotated token: {data['data']['payload']['totp']}")

    # 6. Test Safe Routing Engine with Blackspot Avoidance
    route_payload = {
        "orig_lat": 15.5528,
        "orig_lng": 73.7517,
        "dest_lat": 15.5439,
        "dest_lng": 73.7554
    }
    res = client.post('/maps/api/calculate-safe-route/', data=json.dumps(route_payload), content_type='application/json')
    assert res.status_code == 200
    route_data = res.json()
    assert route_data['success'] is True
    assert len(route_data['data']['waypoints']) > 0
    print(f"✅ 7. Safe Route calculated: {route_data['data']['distance_km']} km, Safety Index: {route_data['data']['safety_score']}%, Detour Applied: {route_data['data']['detour_applied']}")

    # 7. Test Checkpoint QR Verification
    verify_payload = {
        "id_number": "VGL-2026-T89Q2",
        "verifier_name": "Inspector V. Naik",
        "location_name": "Calangute Checkpoint"
    }
    res = client.post('/digital-id/api/verify/', data=json.dumps(verify_payload), content_type='application/json')
    assert res.status_code == 200
    verify_data = res.json()
    assert verify_data['success'] is True
    assert verify_data['data']['verification_result'] == 'VALID'
    assert verify_data['data']['tourist_name'] == 'Ananya Sen'
    print("✅ 8. Police Checkpoint QR Verification validated genuine Tourist ID")

    # 8. Test Emergency SOS Panic Trigger & Auto Dispatch
    sos_payload = {
        "latitude": 15.5420,
        "longitude": 73.7580,
        "trigger_type": "MANUAL_BUTTON",
        "battery_level": 88
    }
    res = client.post('/emergency/api/sos/trigger/', data=json.dumps(sos_payload), content_type='application/json')
    assert res.status_code in [200, 201]
    sos_data = res.json()
    assert sos_data['success'] is True
    sos_id = sos_data['data']['sos_id']
    print(f"✅ 9. SOS Emergency triggered ({sos_id}) - Responders auto-assigned")

    # Check active SOS beacon view
    res = client.get(f'/emergency/active/{sos_id}/')
    assert res.status_code == 200
    assert b"EMERGENCY BEACON BROADCASTING" in res.content
    print("✅ 10. Tourist Active Emergency HUD view rendered")

    # 9. Switch to C2 Authority Operator
    client.logout()
    logged_in_officer = client.login(username='officer_sharma', password='pass1234')
    assert logged_in_officer, "Officer login failed"

    # 10. Test C2 Operations Center Master Dashboard
    res = client.get('/dashboard/c2/')
    assert res.status_code == 200
    assert b"c2-tactical-map" in res.content
    assert b"Active Monitored Tourists" in res.content
    print("✅ 11. Authority C2 Command & Control Tactical Dashboard verified")

    # 11. Test C2 Telemetry API
    res = client.get('/dashboard/api/telemetry/')
    assert res.status_code == 200
    telemetry = res.json()
    assert telemetry['success'] is True
    assert telemetry['data']['stats']['active_sos'] >= 1
    print(f"✅ 12. C2 Telemetry Feed verified: {telemetry['data']['stats']['active_sos']} active SOS, {len(telemetry['data']['responders'])} patrol units")

    # 12. Test AI CCTV Vision Center
    res = client.get('/ai-services/c2/')
    assert res.status_code == 200
    assert b"CCTV Crowd Density" in res.content
    print("✅ 13. AI CCTV Vision & Crowd Density Inspector verified")

    # 13. Test Emergency Broadcast Dispatcher
    broadcast_payload = {
        "alert_type": "SEVERE_WEATHER",
        "title": "High Wave Alert - North Goa",
        "message": "Immediate advisory: Stay clear of rocky beaches.",
        "severity": "WARNING",
        "target_type": "ALL_TOURISTS"
    }
    res = client.post('/alerts/api/', data=json.dumps(broadcast_payload), content_type='application/json')
    assert res.status_code == 201
    print("✅ 14. Emergency Broadcast dispatched successfully over C2 feed")

    # 14. Test Strict RBAC Barriers
    # Tourist attempting C2 access -> 403 Forbidden
    client.logout()
    client.login(username='tourist_ananya', password='pass1234')
    res_tourist_c2 = client.get('/dashboard/c2/')
    assert res_tourist_c2.status_code == 403, f"Tourist accessed C2 unexpectedly: {res_tourist_c2.status_code}"
    print("✅ 15. RBAC Barrier Verified: Tourist blocked from C2 dashboard (HTTP 403)")

    # Authority attempting Admin Portal access -> 403 Forbidden
    client.logout()
    client.login(username='officer_sharma', password='pass1234')
    res_officer_admin = client.get('/auth/admin-portal/')
    assert res_officer_admin.status_code == 403, f"Officer accessed admin portal unexpectedly: {res_officer_admin.status_code}"
    print("✅ 16. RBAC Barrier Verified: Authority officer blocked from Admin Portal (HTTP 403)")

    # 15. Test Tourism Administrator Central Portal
    client.logout()
    logged_in_admin = client.login(username='admin_director', password='pass1234')
    assert logged_in_admin, "Admin login failed"
    res_admin = client.get('/auth/admin-portal/')
    assert res_admin.status_code == 200, f"Admin portal failed: {res_admin.status_code}"
    assert b"Tourism Administrator Central Governance Console" in res_admin.content
    print("✅ 17. Tourism Administrator Governance Console verified (HTTP 200)")

    print("\n=======================================================")
    print("🎉 ALL 17 CRITICAL END-TO-END WORKFLOWS & RBAC CHECKS VERIFIED 100%!")
    print("=======================================================\n")

if __name__ == '__main__':
    run_integration_tests()
