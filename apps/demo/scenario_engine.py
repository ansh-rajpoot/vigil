"""
VIGIL — Controlled SIH Demonstration Engine
Provides deterministic 12-step scenario execution, automated live playback,
and 1-click baseline reset for hackathon evaluation and demonstrations.
"""
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from accounts.models import EmergencyContact
from tourists.models import TouristProfile, TouristLocationHistory
from digital_id.models import DigitalTouristID, IDVerificationLog
from geofencing.models import GeoZone, GeofenceBreachLog
from incidents.models import Incident, IncidentTimeline
from emergency.models import ResponderUnit, SOSAlert, SOSDispatch, SOSLiveBreadcrumb
from risk.models import Blackspot, TouristRiskAssessment
from risk.engine import calculate_tourist_risk
from maps.models import SafetyPOI, SafeRoute
from alerts.models import EmergencyBroadcast
from ai_services.models import VisionCameraFeed, VisionDetectionLog
from common.utils import generate_secure_crypto_hash

User = get_user_model()


def broadcast_to_c2(event_type: str, data: dict):
    """Utility to push real-time event to C2 operations WebSocket desk."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "c2_operations_feed",
                {
                    "type": "c2_broadcast_event",
                    "data": {
                        "type": event_type,
                        **data,
                        "is_demo": True,
                        "timestamp": timezone.now().isoformat()
                    }
                }
            )
    except Exception as e:
        print(f"Demo broadcast error: {e}")


def broadcast_to_tourist(user_id: int, event_type: str, data: dict):
    """Utility to push personal alert to tourist device WebSocket."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"tourist_alerts_{user_id}",
                {
                    "type": "tourist_push_notification",
                    "data": {
                        "type": event_type,
                        **data,
                        "is_demo": True,
                        "timestamp": timezone.now().isoformat()
                    }
                }
            )
    except Exception as e:
        print(f"Demo tourist push error: {e}")


def reset_to_demo_baseline():
    """
    Wipes all transient demonstration state and seeds a clean, deterministic baseline.
    All data is clearly tagged with [DEMO SCENARIO].
    """
    # 1. Clear existing dynamic tables
    IncidentTimeline.objects.all().delete()
    Incident.objects.all().delete()
    SOSLiveBreadcrumb.objects.all().delete()
    SOSDispatch.objects.all().delete()
    SOSAlert.objects.all().delete()
    GeofenceBreachLog.objects.all().delete()
    VisionDetectionLog.objects.all().delete()
    EmergencyBroadcast.objects.all().delete()
    TouristLocationHistory.objects.all().delete()
    TouristRiskAssessment.objects.all().delete()

    # 2. Ensure Core Authority Officer exists
    officer, _ = User.objects.get_or_create(
        username='officer_sharma',
        defaults={
            'email': 'c2.ops@vigil.gov.in',
            'first_name': 'Rajesh',
            'last_name': 'Sharma',
            'role': 'OPERATOR',
            'badge_number': 'GOA-POL-8821',
            'agency_name': 'Goa Police C2 Task Force [DEMO]',
            'is_verified': True
        }
    )
    officer.set_password('pass1234')
    officer.save()

    # 3. Ensure Tourism Admin exists
    admin_user, _ = User.objects.get_or_create(
        username='admin_director',
        defaults={
            'email': 'director.tourism@goa.gov.in',
            'first_name': 'Sunil',
            'last_name': 'Deshmukh',
            'role': 'ADMIN',
            'badge_number': 'GOA-ADM-001',
            'agency_name': 'Goa Tourism Board [DEMO]',
            'is_verified': True,
            'is_staff': True,
            'is_superuser': True
        }
    )
    admin_user.set_password('pass1234')
    admin_user.save()

    # 4. Ensure Responder Units exist and are AVAILABLE
    ResponderUnit.objects.all().delete()
    pcr1 = ResponderUnit.objects.create(
        unit_code='PCR-PANJIM-01',
        agency='POLICE',
        callsign='Patrol Alpha PCR-01 [DEMO]',
        officer_in_charge='Head Constable S. Naik',
        contact_number='+91 94220 11001',
        status='AVAILABLE',
        current_latitude=15.4950,
        current_longitude=73.8240,
        station_base_name='Panaji Police HQ'
    )
    pcr2 = ResponderUnit.objects.create(
        unit_code='PCR-CALANGUTE-03',
        agency='TOURIST_POLICE',
        callsign='Coastal Patrol PCR-03 [DEMO]',
        officer_in_charge='Sub-Inspector R. Govekar',
        contact_number='+91 94220 11003',
        status='AVAILABLE',
        current_latitude=15.5400,
        current_longitude=73.7550,
        station_base_name='Calangute Tourist Police Station'
    )
    ems1 = ResponderUnit.objects.create(
        unit_code='108-EMS-02',
        agency='AMBULANCE',
        callsign='108 EMS Ambulance 02 [DEMO]',
        officer_in_charge='Paramedic D. Fernandes',
        contact_number='+91 94220 10802',
        status='AVAILABLE',
        current_latitude=15.5100,
        current_longitude=73.8150,
        station_base_name='Bambolim Trauma Center'
    )

    # 5. Ensure Geofences and Blackspots
    GeoZone.objects.all().delete()
    zone_safe = GeoZone.objects.create(
        name='Panaji Heritage Promenade [DEMO]',
        code='ZONE-PANAJI-HERITAGE',
        zone_type='SAFE',
        center_latitude=15.4989,
        center_longitude=73.8278,
        radius_meters=450,
        polygon_geojson={
            "type": "Polygon",
            "coordinates": [[[73.825, 15.496], [73.831, 15.496], [73.831, 15.502], [73.825, 15.502], [73.825, 15.496]]]
        }
    )
    zone_caution = GeoZone.objects.create(
        name='Anjuna Rocky Shoreline [DEMO]',
        code='ZONE-ANJUNA-ROCKS',
        zone_type='CAUTION',
        center_latitude=15.5800,
        center_longitude=73.7420,
        radius_meters=350,
        polygon_geojson={
            "type": "Polygon",
            "coordinates": [[[73.738, 15.577], [73.746, 15.577], [73.746, 15.583], [73.738, 15.583], [73.738, 15.577]]]
        }
    )
    zone_restricted = GeoZone.objects.create(
        name='Vagator Cliffs Prohibited Edge [DEMO]',
        code='ZONE-VAGATOR-CLIFFS',
        zone_type='RESTRICTED',
        center_latitude=15.6030,
        center_longitude=73.7330,
        radius_meters=300,
        polygon_geojson={
            "type": "Polygon",
            "coordinates": [[[73.730, 15.600], [73.736, 15.600], [73.736, 15.606], [73.730, 15.606], [73.730, 15.600]]]
        }
    )

    # 6. Ensure Safety POIs (Hospitals and Police Outposts)
    SafetyPOI.objects.all().delete()
    SafetyPOI.objects.create(
        name='Goa Medical College & Hospital [DEMO]',
        poi_type='HOSPITAL',
        latitude=15.4605,
        longitude=73.8565,
        contact_number='+91 832 245 8725',
        address='Bambolim, Goa'
    )
    SafetyPOI.objects.create(
        name='North District Hospital Mapusa [DEMO]',
        poi_type='HOSPITAL',
        latitude=15.5920,
        longitude=73.8150,
        contact_number='+91 832 226 2372',
        address='Mapusa, Goa'
    )
    SafetyPOI.objects.create(
        name='Panaji Police Station HQ [DEMO]',
        poi_type='POLICE',
        latitude=15.4989,
        longitude=73.8240,
        contact_number='112',
        address='Church Square, Panaji'
    )
    SafetyPOI.objects.create(
        name='Calangute Tourist Police Kiosk [DEMO]',
        poi_type='TOURIST_POLICE',
        latitude=15.5420,
        longitude=73.7570,
        contact_number='112',
        address='Calangute Beach Promenade'
    )

    # 7. Ensure Camera Feeds
    VisionCameraFeed.objects.all().delete()
    cam1 = VisionCameraFeed.objects.create(
        camera_code='CAM-CALANGUTE-01',
        location_name='Calangute Main Market Promenade [DEMO]',
        zone=zone_safe,
        latitude=15.5415,
        longitude=73.7575,
        max_safe_capacity=120,
        critical_threshold_count=90,
        surge_threshold_rate=20,
        coverage_area_sqm=220.0,
        is_active=True
    )
    VisionDetectionLog.objects.create(
        camera=cam1,
        crowd_count=22,
        crowd_density_score=24.5,
        density_tier='LOW',
        people_per_sqm=0.1,
        surge_rate_per_min=1.2,
        concentration_index=0.28,
        anomaly_detected='NONE',
        notes='[DEMO SCENARIO] Normal tourist footfall recorded.'
    )

    # 8. Ensure Primary Demo Tourist (Ananya) at Safe Initial Position
    u1, _ = User.objects.get_or_create(
        username='tourist_ananya',
        defaults={
            'first_name': 'Ananya',
            'last_name': 'Sen',
            'role': 'TOURIST',
            'phone_number': '+91 98765 12345',
            'is_verified': True
        }
    )
    u1.set_password('pass1234')
    u1.save()

    p1, _ = TouristProfile.objects.get_or_create(
        user=u1,
        defaults={
            'nationality': 'Indian',
            'blood_group': 'O+',
            'destination_city': 'Goa, India',
            'hotel_stay_details': 'Taj Fort Aguada Resort, Candolim',
            'current_latitude': 15.4989,
            'current_longitude': 73.8278,
            'trip_status': 'ACTIVE',
            'battery_level': 88,
            'last_location_time': timezone.now()
        }
    )
    p1.current_latitude = 15.4989
    p1.current_longitude = 73.8278
    p1.trip_status = 'ACTIVE'
    p1.battery_level = 88
    p1.save()

    # Digital ID for Ananya
    DigitalTouristID.objects.filter(tourist=p1).delete()
    DigitalTouristID.objects.create(
        tourist=p1,
        id_number='VGL-2026-T8810',
        crypto_hash='hash_ananya_sih_demo_2026',
        valid_until=timezone.now() + timedelta(days=30),
        verification_token_secret='secret_demo_ananya'
    )

    # Initial Safe Risk Assessment
    TouristRiskAssessment.objects.create(
        tourist=p1,
        overall_score=14,
        risk_level='SAFE',
        spatial_risk_score=4,
        temporal_risk_score=3,
        isolation_risk_score=2,
        crowd_risk_score=2,
        device_health_score=3,
        primary_risk_factor='[DEMO] Monitored Safe Tourist Corridor',
        ai_recommendation='Area has high tourist police presence and continuous illumination.'
    )

    # Secondary Tourists for Population
    tourist_data = [
        ('tourist_marcus', 'Marcus', 'Weber', 'German', 'A+', 15.5420, 73.7570, 75, 'ACTIVE'),
        ('tourist_elena', 'Elena', 'Rostova', 'Russian', 'B+', 15.5800, 73.7420, 45, 'ACTIVE'),
        ('tourist_vikram', 'Vikram', 'Malhotra', 'Indian', 'AB+', 15.5120, 73.8310, 92, 'ACTIVE'),
        ('tourist_chloe', 'Chloe', 'Dubois', 'French', 'O-', 15.6010, 73.7360, 28, 'ACTIVE'),
    ]

    for uname, fname, lname, nat, bg, lat, lng, batt, status in tourist_data:
        tu, _ = User.objects.get_or_create(
            username=uname,
            defaults={'first_name': fname, 'last_name': lname, 'role': 'TOURIST', 'phone_number': '+91 98765 00000', 'is_verified': True}
        )
        tu.set_password('pass1234')
        tu.save()

        tp, _ = TouristProfile.objects.get_or_create(
            user=tu,
            defaults={'nationality': nat, 'blood_group': bg, 'destination_city': 'Goa, India', 'current_latitude': lat, 'current_longitude': lng, 'trip_status': status, 'battery_level': batt}
        )
        tp.current_latitude = lat
        tp.current_longitude = lng
        tp.trip_status = status
        tp.battery_level = batt
        tp.save()

    # Active Emergency Broadcast
    EmergencyBroadcast.objects.create(
        alert_type='SEVERE_WEATHER',
        title='[DEMO] High Wave & Swell Caution Notice',
        message='Coast Guard advisory: Rough sea conditions along North Goa cliffs. Avoid unpatrolled rocky points.',
        severity='WARNING',
        target_type='ALL_TOURISTS',
        issued_by=officer,
        is_active=True,
        starts_at=timezone.now() - timedelta(hours=1),
        expires_at=timezone.now() + timedelta(hours=23)
    )

    # Initial Baseline Incident
    Incident.objects.create(
        incident_id='INC-2026-DEMO01',
        reporter=u1,
        reporter_name='Ananya Sen',
        reporter_phone='+91 98765 12345',
        title='[DEMO] Lost Shoulder Bag in Panaji Market',
        description='Reported lost bag near municipal garden. Items secured at station kiosk.',
        category='LOST_PROPERTY',
        severity='LOW',
        status='VERIFIED',
        latitude=15.4975,
        longitude=73.8260,
        location_name='Panaji Municipal Garden'
    )

    return {
        'status': 'success',
        'message': 'Baseline demo state restored successfully.',
        'timestamp': timezone.now().isoformat()
    }


def execute_demo_step(step_id: int) -> dict:
    """
    Executes a designated step (1 to 12) of the live SIH demonstration flow.
    """
    now = timezone.now()
    p1 = TouristProfile.objects.filter(user__username='tourist_ananya').first()
    if not p1:
        reset_to_demo_baseline()
        p1 = TouristProfile.objects.get(user__username='tourist_ananya')

    # STEP 1: Several Tourists Appear on Map
    if step_id == 1:
        tourists = TouristProfile.objects.filter(trip_status='ACTIVE')
        broadcast_to_c2("tourists_sync", {
            "message": "5 Active Tourists Synchronized on Tactical GIS Map",
            "count": tourists.count()
        })
        return {
            "step": 1,
            "title": "Tourists Appear on Tactical Map",
            "description": f"{tourists.count()} registered tourists are active and streaming GPS positions across North and Central Goa.",
            "data": {"tourist_count": tourists.count()}
        }

    # STEP 2: Varied Risk Levels Assigned
    elif step_id == 2:
        # Assign different risk tiers
        for tp in TouristProfile.objects.all():
            score = 15 if tp.user.username == 'tourist_ananya' else 45 if tp.user.username == 'tourist_elena' else 68 if tp.user.username == 'tourist_chloe' else 22
            level = 'SAFE' if score <= 30 else 'MODERATE' if score <= 60 else 'HIGH'
            TouristRiskAssessment.objects.create(
                tourist=tp,
                overall_score=score,
                risk_level=level,
                primary_risk_factor=f"[DEMO] Factor: {level} Risk Corridor",
                ai_recommendation="Safety profile evaluated based on time of day, battery, and location."
            )
        broadcast_to_c2("risk_distribution_update", {
            "message": "Multi-tier risk distribution calculated across tourist population."
        })
        return {
            "step": 2,
            "title": "Tourists Evaluated with Varied Risk Levels",
            "description": "Risk distribution active: Safe (Ananya/Vikram), Moderate (Elena), High (Chloe).",
            "data": {"safe": 2, "moderate": 1, "high": 1, "critical": 0}
        }

    # STEP 3: Tourist Enters High-Risk Zone (Vagator Cliffs)
    elif step_id == 3:
        # Move Ananya to Vagator Cliffs restricted edge
        p1.current_latitude = 15.6030
        p1.current_longitude = 73.7330
        p1.save(update_fields=['current_latitude', 'current_longitude'])

        zone_restricted = GeoZone.objects.filter(code='ZONE-VAGATOR-CLIFFS').first()
        breach = GeofenceBreachLog.objects.create(
            tourist=p1,
            zone=zone_restricted,
            breach_type='ENTRY',
            latitude=15.6030,
            longitude=73.7330,
            is_acknowledged=False
        )

        broadcast_to_c2("high_risk_zone_entry", {
            "tourist_name": "Ananya Sen",
            "zone_name": "Vagator Cliffs Prohibited Edge",
            "latitude": 15.6030,
            "longitude": 73.7330
        })

        return {
            "step": 3,
            "title": "Tourist Enters Restricted High-Risk Zone",
            "description": "Ananya Sen entered 'Vagator Cliffs Prohibited Edge'. Geofence entry breach logged.",
            "data": {"latitude": 15.6030, "longitude": 73.7330, "zone": "Vagator Cliffs"}
        }

    # STEP 4: Risk Score Increases
    elif step_id == 4:
        assessment = calculate_tourist_risk(p1, 15.6030, 73.7330)
        p1.refresh_from_db()
        broadcast_to_c2("risk_score_elevated", {
            "tourist_id": p1.user.id,
            "tourist_name": "Ananya Sen",
            "new_score": assessment.overall_score,
            "risk_level": assessment.risk_level
        })
        return {
            "step": 4,
            "title": "Tourist Risk Score Increases Dynamically",
            "description": f"Ananya's composite risk score elevated to {assessment.overall_score}/100 [{assessment.risk_level}] due to proximity to cliff drop-off.",
            "data": {"score": assessment.overall_score, "level": assessment.risk_level}
        }

    # STEP 5: Tourist Receives Warning
    elif step_id == 5:
        broadcast_to_tourist(p1.user.id, "geofence_warning", {
            "title": "⚠️ RESTRICTED CLIFF PERIMETER WARNING",
            "message": "You have crossed into the unpatrolled Vagator Cliff perimeter. Immediate advisory: Step back 50m to designated tourist path."
        })
        return {
            "step": 5,
            "title": "Tourist Receives Immediate Device Warning",
            "description": "Push notification sent to Ananya's device alerting her of the hazardous terrain.",
            "data": {"recipient": "Ananya Sen", "status": "DELIVERED"}
        }

    # STEP 6: Tourist Triggers SOS
    elif step_id == 6:
        sos, created = SOSAlert.objects.get_or_create(
            sos_id='SOS-2026-DEMO01',
            defaults={
                'tourist': p1,
                'status': 'ACTIVE',
                'latitude': 15.6030,
                'longitude': 73.7330,
                'battery_level': 85,
                'emergency_notes': '[DEMO SCENARIO] Slipped on wet rock near cliff edge; injured ankle and unable to climb back.'
            }
        )
        p1.trip_status = 'SOS_ACTIVE'
        p1.save(update_fields=['trip_status'])

        return {
            "step": 6,
            "title": "Tourist Activates SOS Panic Beacon",
            "description": f"Emergency beacon {sos.sos_id} triggered with live coordinates, battery level, and emergency note.",
            "data": {"sos_id": sos.sos_id, "status": "ACTIVE"}
        }

    # STEP 7: Authority Receives Live SOS
    elif step_id == 7:
        sos = SOSAlert.objects.filter(sos_id='SOS-2026-DEMO01').first()
        broadcast_to_c2("new_sos", {
            "sos_id": sos.sos_id if sos else "SOS-2026-DEMO01",
            "tourist_name": "Ananya Sen",
            "phone_number": "+91 98765 12345",
            "blood_group": "O+",
            "latitude": 15.6030,
            "longitude": 73.7330,
            "battery": 85,
            "notes": "Slipped on wet rock near cliff edge; injured ankle."
        })
        return {
            "step": 7,
            "title": "Authority C2 Operations Center Receives Live SOS",
            "description": "Audio chime triggered, Active SOS counter incremented to 1, and alert prepended to live triage feed.",
            "data": {"c2_feed": "PREPENDED", "audio_alert": True}
        }

    # STEP 8: Incident Appears on Map
    elif step_id == 8:
        broadcast_to_c2("map_marker_pulse", {
            "layer": "sos",
            "latitude": 15.6030,
            "longitude": 73.7330,
            "title": "SOS-2026-DEMO01 (Ananya Sen)"
        })
        return {
            "step": 8,
            "title": "SOS Emergency Marker Rendered on Tactical GIS Map",
            "description": "Leaflet map animates and pans to Vagator Cliffs coordinates with pulsating red emergency beacon.",
            "data": {"latitude": 15.6030, "longitude": 73.7330, "pin_type": "PULSING_RED_BEACON"}
        }

    # STEP 9: Authority Acknowledges
    elif step_id == 9:
        sos = SOSAlert.objects.filter(sos_id='SOS-2026-DEMO01').first()
        if sos:
            sos.status = 'ACKNOWLEDGED'
            sos.acknowledged_at = timezone.now()
            sos.save(update_fields=['status', 'acknowledged_at'])

        broadcast_to_tourist(p1.user.id, "sos_acknowledgement", {
            "sos_id": "SOS-2026-DEMO01",
            "status": "ACKNOWLEDGED",
            "officer_badge": "GOA-POL-8821",
            "message": "C2 Dispatch Desk has acknowledged your emergency. Responders are being mobilized."
        })
        broadcast_to_c2("sos_status_change", {
            "sos_id": "SOS-2026-DEMO01",
            "status": "ACKNOWLEDGED"
        })

        return {
            "step": 9,
            "title": "C2 Operator Acknowledges Emergency Alert",
            "description": "Status updated to ACKNOWLEDGED. Confirmation receipt sent to Ananya's mobile HUD.",
            "data": {"status": "ACKNOWLEDGED", "acknowledged_by": "Officer Rajesh Sharma (GOA-POL-8821)"}
        }

    # STEP 10: Authority Responds & Dispatches Unit
    elif step_id == 10:
        sos = SOSAlert.objects.filter(sos_id='SOS-2026-DEMO01').first()
        pcr = ResponderUnit.objects.filter(unit_code='PCR-CALANGUTE-03').first() or ResponderUnit.objects.first()

        if sos and pcr:
            sos.status = 'RESPONDING'
            sos.save(update_fields=['status'])

            pcr.status = 'DISPATCHED'
            pcr.save(update_fields=['status'])

            SOSDispatch.objects.create(
                sos=sos,
                responder=pcr,
                dispatch_status='DISPATCHED',
                eta_minutes=4.0,
                notes='[DEMO] Unit dispatched with first-aid trauma kit.'
            )

        broadcast_to_tourist(p1.user.id, "authority_response", {
            "sos_id": "SOS-2026-DEMO01",
            "status": "RESPONDING",
            "callsign": pcr.callsign if pcr else "Coastal Patrol PCR-03",
            "eta_minutes": 4.0
        })
        broadcast_to_c2("sos_responder_dispatched", {
            "sos_id": "SOS-2026-DEMO01",
            "callsign": pcr.callsign if pcr else "Coastal Patrol PCR-03",
            "eta_minutes": 4.0
        })

        return {
            "step": 10,
            "title": "Authority Dispatches Nearest Patrol Unit",
            "description": f"Assigned {pcr.callsign if pcr else 'Coastal Patrol'} to on-scene rescue with 4.0-min ETA.",
            "data": {"unit": pcr.callsign if pcr else "PCR-03", "eta": "4.0 min"}
        }

    # STEP 11: Incident is Resolved
    elif step_id == 11:
        sos = SOSAlert.objects.filter(sos_id='SOS-2026-DEMO01').first()
        pcr = ResponderUnit.objects.filter(unit_code='PCR-CALANGUTE-03').first() or ResponderUnit.objects.first()

        if sos:
            sos.status = 'RESOLVED'
            sos.resolved_at = timezone.now()
            sos.emergency_notes = '[DEMO SCENARIO] Tourist successfully located on cliff trail. First aid administered to sprained ankle; tourist safely escorted back to hotel.'
            sos.save(update_fields=['status', 'resolved_at', 'emergency_notes'])

        if pcr:
            pcr.status = 'AVAILABLE'
            pcr.save(update_fields=['status'])

        p1.trip_status = 'ACTIVE'
        p1.save(update_fields=['trip_status'])

        broadcast_to_tourist(p1.user.id, "sos_resolved", {
            "sos_id": "SOS-2026-DEMO01",
            "status": "RESOLVED",
            "notes": "Emergency safely resolved. Stay safe!"
        })
        broadcast_to_c2("sos_resolved_event", {
            "sos_id": "SOS-2026-DEMO01",
            "status": "RESOLVED"
        })

        return {
            "step": 11,
            "title": "Emergency Successfully Resolved",
            "description": "Tourist status reset to ACTIVE, responder unit returned to AVAILABLE, and full audit notes saved.",
            "data": {"status": "RESOLVED", "responder_status": "AVAILABLE"}
        }

    # STEP 12: Analytics Update
    elif step_id == 12:
        from dashboard.views import get_analytics_metrics
        analytics = get_analytics_metrics(time_range='today')
        broadcast_to_c2("analytics_refresh", {"analytics": analytics})

        return {
            "step": 12,
            "title": "Operations Analytics & KPIs Updated",
            "description": f"Real-time analytics re-aggregated: {analytics['kpis']['total_incidents']} cases logged, avg response time: {analytics['kpis']['avg_response_minutes']} min.",
            "data": analytics['kpis']
        }

    return {
        "step": step_id,
        "error": "Invalid step number. Choose between 1 and 12."
    }
