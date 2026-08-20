import os
import sys
import django
from datetime import timedelta

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vigil_core.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import EmergencyContact
from tourists.models import TouristProfile, TouristLocationHistory
from digital_id.models import DigitalTouristID, IDVerificationLog
from geofencing.models import GeoZone, GeofenceBreachLog
from incidents.models import Incident, IncidentTimeline
from emergency.models import ResponderUnit, SOSAlert, SOSDispatch, SOSLiveBreadcrumb
from risk.models import Blackspot, TouristRiskAssessment
from maps.models import SafetyPOI, SafeRoute
from alerts.models import EmergencyBroadcast
from ai_services.models import VisionCameraFeed, VisionDetectionLog
from common.utils import generate_secure_crypto_hash

User = get_user_model()

def populate():
    print("🌱 Seeding realistic Smart India Hackathon (SIH) demo data for VIGIL...")

    # 1. Clear existing data
    User.objects.all().delete()
    GeoZone.objects.all().delete()
    Blackspot.objects.all().delete()
    SafetyPOI.objects.all().delete()
    SafeRoute.objects.all().delete()
    ResponderUnit.objects.all().delete()
    VisionCameraFeed.objects.all().delete()
    EmergencyBroadcast.objects.all().delete()

    # 2. Create Users
    # 2a. Tourism Administrator (Top-tier RBAC)
    admin_user = User.objects.create_user(
        username='admin_director',
        email='director.tourism@goa.gov.in',
        password='pass1234',
        first_name='Sunil',
        last_name='Deshmukh',
        role='ADMIN',
        badge_number='GOA-ADM-001',
        agency_name='Goa Department of Tourism & Public Safety',
        is_verified=True,
        is_staff=True,
        is_superuser=True
    )
    print(f"Created Tourism Administrator: {admin_user.username}")

    # 2b. Authority C2 Officer
    officer = User.objects.create_user(
        username='officer_sharma',
        email='c2.ops@vigil.gov.in',
        password='pass1234',
        first_name='Rajesh',
        last_name='Sharma',
        role='OPERATOR',
        badge_number='GOA-POL-8821',
        agency_name='Goa Police & Tourism Task Force',
        is_verified=True,
        is_staff=False,
        is_superuser=False
    )
    print(f"Created C2 Officer: {officer.username}")

    # Tourist 1 (Ananya)
    tourist1_user = User.objects.create_user(
        username='tourist_ananya',
        email='ananya.sen@example.com',
        password='pass1234',
        first_name='Ananya',
        last_name='Sen',
        role='TOURIST',
        phone_number='+91 98765 12345',
        is_verified=True
    )

    profile1 = TouristProfile.objects.create(
        user=tourist1_user,
        nationality='Indian',
        blood_group='O+',
        destination_city='Greater Noida & Noida, NCR',
        hotel_stay_details='Radisson Blu Hotel, Knowledge Park / Pari Chowk, Greater Noida',
        medical_conditions='Mild Asthma (Inhaler in backpack)',
        allergies='Penicillin',
        trip_start_date=timezone.now().date(),
        trip_end_date=timezone.now().date() + timedelta(days=7),
        trip_status='ACTIVE',
        current_latitude=28.4744,
        current_longitude=77.5040,
        last_location_time=timezone.now(),
        battery_level=92
    )

    EmergencyContact.objects.create(
        user=tourist1_user,
        name='Vikram Sen',
        relationship='Spouse',
        phone_number='+91 98765 99999',
        email='vikram.sen@example.com',
        is_primary=True
    )
    EmergencyContact.objects.create(
        user=tourist1_user,
        name='Meera Sen',
        relationship='Sister',
        phone_number='+91 98765 88888',
        email='meera.sen@example.com',
        is_primary=False
    )

    # Digital ID for Tourist 1
    did1 = DigitalTouristID.objects.create(
        tourist=profile1,
        id_number='VGL-2026-T89Q2',
        crypto_hash=generate_secure_crypto_hash('tourist_ananya:VGL-2026-T89Q2:sih_secret_key_2026'),
        status='ACTIVE',
        valid_until=timezone.now() + timedelta(days=30),
        verification_token_secret='sih_secret_key_2026_ananya'
    )
    did1.generate_qr_code()

    # Risk Assessment for Tourist 1
    TouristRiskAssessment.objects.create(
        tourist=profile1,
        overall_score=14,
        risk_level='SAFE',
        spatial_risk_score=10,
        temporal_risk_score=10,
        isolation_risk_score=12,
        crowd_risk_score=8,
        device_health_score=5,
        primary_risk_factor='Secure Tourist Promenade',
        ai_recommendation='You are in a well-lit tourist zone with active police patrol presence.'
    )
    print(f"Created Tourist: {tourist1_user.username} (ID: {did1.id_number})")

    # Tourist 2 (Rahul)
    tourist2_user = User.objects.create_user(
        username='tourist_rahul',
        email='rahul.verma@example.com',
        password='pass1234',
        first_name='Rahul',
        last_name='Verma',
        role='TOURIST',
        phone_number='+91 98111 22334',
        is_verified=True
    )

    profile2 = TouristProfile.objects.create(
        user=tourist2_user,
        nationality='Indian',
        blood_group='B+',
        destination_city='Goa, India',
        hotel_stay_details='Goa Marriott Resort, Miramar, Panaji',
        trip_start_date=timezone.now().date(),
        trip_end_date=timezone.now().date() + timedelta(days=5),
        trip_status='ACTIVE',
        current_latitude=15.5528,
        current_longitude=73.7517,
        last_location_time=timezone.now(),
        battery_level=78
    )

    did2 = DigitalTouristID.objects.create(
        tourist=profile2,
        id_number='VGL-2026-K44R1',
        crypto_hash=generate_secure_crypto_hash('tourist_rahul:VGL-2026-K44R1:sih_secret_key_2026'),
        status='ACTIVE',
        valid_until=timezone.now() + timedelta(days=30),
        verification_token_secret='sih_secret_key_2026_rahul'
    )
    did2.generate_qr_code()

    # 3. Create Responder Units
    r1 = ResponderUnit.objects.create(
        unit_code='PCR-PANJIM-01',
        agency='POLICE',
        callsign='PCR-PANJIM-01 (Patrol Alpha)',
        officer_in_charge='Head Constable S. Naik',
        contact_number='+91 94220 11001',
        status='AVAILABLE',
        current_latitude=15.4950,
        current_longitude=73.8240,
        station_base_name='Panaji Police Station'
    )
    r2 = ResponderUnit.objects.create(
        unit_code='PCR-CALANGUTE-04',
        agency='TOURISM_POLICE',
        callsign='TOURISM-PATROL-CALANGUTE',
        officer_in_charge='Sub-Inspector V. Patil',
        contact_number='+91 94220 11004',
        status='AVAILABLE',
        current_latitude=15.5420,
        current_longitude=73.7580,
        station_base_name='Calangute Tourist Outpost'
    )
    r3 = ResponderUnit.objects.create(
        unit_code='108-EMS-NORTH-02',
        agency='AMBULANCE',
        callsign='108-EMS-AMBULANCE-02',
        officer_in_charge='Paramedic D. Fernandes',
        contact_number='+91 94220 10802',
        status='AVAILABLE',
        current_latitude=15.5100,
        current_longitude=73.8150,
        station_base_name='GMC Emergency Outpost'
    )
    print("Created 3 Field Responder Units.")

    # 4. Create GeoZones
    # Zone 1: Panaji Safe Haven
    GeoZone.objects.create(
        name='Panaji Riverside Safe Promenade',
        code='ZONE-PANJIM-SAFE',
        zone_type='SAFE',
        description='Designated high-security tourist promenade with 24x7 police kiosks and continuous illumination.',
        center_latitude=15.4989,
        center_longitude=73.8278,
        polygon_geojson={
            "type": "Polygon",
            "coordinates": [[
                [73.8200, 15.4920],
                [73.8350, 15.4920],
                [73.8350, 15.5050],
                [73.8200, 15.5050],
                [73.8200, 15.4920]
            ]]
        },
        safety_advisory='Secure zone with high tourist police density and CCTV surveillance.'
    )

    # Zone 2: Aguada Rocky Cliff High Risk
    GeoZone.objects.create(
        name='Fort Aguada Rocky Cliffside Perimeter',
        code='ZONE-AGUADA-CLIFF',
        zone_type='HIGH_RISK',
        description='Dangerous steep cliff with loose rocks and high wave surge risk.',
        center_latitude=15.4920,
        center_longitude=73.7730,
        polygon_geojson={
            "type": "Polygon",
            "coordinates": [[
                [73.7680, 15.4880],
                [73.7780, 15.4880],
                [73.7780, 15.4960],
                [73.7680, 15.4960],
                [73.7680, 15.4880]
            ]]
        },
        safety_advisory='CAUTION: High risk cliff drop. Do not cross warning fences.'
    )

    # Zone 3: Baga Late-Night Caution Zone
    GeoZone.objects.create(
        name='Baga Creek Caution Area',
        code='ZONE-BAGA-CAUTION',
        zone_type='CAUTION',
        description='Heightened vigilance area during late evening hours to prevent water accidents.',
        center_latitude=15.5580,
        center_longitude=73.7540,
        curfew_start_time='23:00:00',
        curfew_end_time='06:00:00',
        polygon_geojson={
            "type": "Polygon",
            "coordinates": [[
                [73.7500, 15.5520],
                [73.7600, 15.5520],
                [73.7600, 15.5640],
                [73.7500, 15.5640],
                [73.7500, 15.5520]
            ]]
        },
        safety_advisory='CAUTION ZONE: Heightened vigilance advised after 23:00 hrs.'
    )

    # 4b. Multi-City GeoZones
    # Mumbai Zone: Gateway & Colaba Safe Plaza
    GeoZone.objects.create(
        name='Gateway of India & Colaba High-Security Plaza',
        code='ZONE-MUM-GATEWAY',
        zone_type='SAFE_HAVEN',
        description='24x7 Coastal Police & CISF Monitored Tourist Plaza.',
        center_latitude=18.9220,
        center_longitude=72.8347,
        polygon_geojson={
            "type": "Polygon",
            "coordinates": [[[72.828, 18.916], [72.840, 18.916], [72.840, 18.928], [72.828, 18.928], [72.828, 18.916]]]
        },
        safety_advisory='SAFE HAVEN: Dedicated Tourist Police assistance booths and active CCTV coverage.'
    )
    # Delhi Zone: India Gate Central Vista Safe Corridor
    GeoZone.objects.create(
        name='India Gate & Kartavya Path High-Security Zone',
        code='ZONE-DEL-KARTAVYA',
        zone_type='SAFE_HAVEN',
        description='Central Vista high-security monitored pedestrian promenade.',
        center_latitude=28.6129,
        center_longitude=77.2295,
        polygon_geojson={
            "type": "Polygon",
            "coordinates": [[[77.220, 28.605], [77.240, 28.605], [77.240, 28.620], [77.220, 28.620], [77.220, 28.605]]]
        },
        safety_advisory='SAFE HAVEN: Paramilitary & Delhi Police round-the-clock patrol corridor.'
    )
    # Agra Zone: Taj Mahal 500m Eco-Protection Buffer
    GeoZone.objects.create(
        name='Taj Mahal High-Security & Eco-Protection Perimeter',
        code='ZONE-AGR-TAJ-BUFFER',
        zone_type='SAFE_HAVEN',
        description='Pedestrianized non-combustion vehicle security perimeter.',
        center_latitude=27.1751,
        center_longitude=78.0421,
        polygon_geojson={
            "type": "Polygon",
            "coordinates": [[[78.035, 27.170], [78.050, 27.170], [78.050, 27.182], [78.035, 27.182], [78.035, 27.170]]]
        },
        safety_advisory='SAFE HAVEN: Multi-tier security checkposts and 24x7 Tourist Police Desk.'
    )
    # Jaipur Zone: Walled Pink City Heritage Corridor
    GeoZone.objects.create(
        name='Jaipur Walled Pink City Monitored Corridor',
        code='ZONE-JAI-WALLED-CITY',
        zone_type='SAFE_HAVEN',
        description='Heritage tourist zone covering Hawa Mahal, City Palace, and Johari Bazaar.',
        center_latitude=26.9239,
        center_longitude=75.8267,
        polygon_geojson={
            "type": "Polygon",
            "coordinates": [[[75.815, 26.915], [75.835, 26.915], [75.835, 26.932], [75.815, 26.932], [75.815, 26.915]]]
        },
        safety_advisory='SAFE HAVEN: Rajasthan Tourist Police Station active at Badi Choupad.'
    )
    # Noida Zone: Sector 18 Commercial Safety Grid
    GeoZone.objects.create(
        name='Noida Sector 18 Commercial & Entertainment Safety Grid',
        code='ZONE-NOI-SEC18',
        zone_type='SAFE_HAVEN',
        description='Integrated urban shopping hub with high-density CCTV and Pink Police Booths.',
        center_latitude=28.5708,
        center_longitude=77.3216,
        polygon_geojson={
            "type": "Polygon",
            "coordinates": [[[77.315, 28.562], [77.328, 28.562], [77.328, 28.578], [77.315, 28.578], [77.315, 28.562]]]
        },
        safety_advisory='SAFE HAVEN: UP 112 Rapid PCR Response and Pink Police Women Assistance Post.'
    )
    print("Created 9 Multi-City Geo-Fence Zones.")

    # 5b. Multi-City Blackspots
    Blackspot.objects.create(
        name='Mumbai Bandra Bandstand Rocky Tidal Slip Zone',
        category='WATER_HAZARD',
        risk_weight=75,
        latitude=19.0430,
        longitude=72.8190,
        radius_meters=300,
        incident_count_30d=4,
        safety_advice='High tide waves submerge slippery coastal boulders. Do not cross warning railings.'
    )
    Blackspot.objects.create(
        name='Delhi Chandni Chowk High-Density Chokepoint',
        category='THEFT_PRONE',
        risk_weight=70,
        latitude=28.6506,
        longitude=77.2303,
        radius_meters=350,
        incident_count_30d=8,
        safety_advice='Crowded marketplace. Keep wallets and valuables in front compartments.'
    )
    Blackspot.objects.create(
        name='Jaipur Nahargarh Cliffhead Unprotected Edge',
        category='ACCIDENT_PRONE',
        risk_weight=85,
        latitude=26.9373,
        longitude=75.8155,
        radius_meters=250,
        incident_count_30d=5,
        safety_advice='Steep vertical drop along the fort ridge. Remain on paved viewing pavilions.'
    )
    print("Created 6 Multi-City Crime/Hazard Blackspots.")

    # 6b. Multi-City Safety POIs (Police & Hospitals)
    # =========================================================================
    # MUMBAI SAFETY POIs
    # =========================================================================
    SafetyPOI.objects.create(
        name='Colaba Tourist Police Assistance Station',
        poi_type='TOURIST_POLICE',
        latitude=18.9220,
        longitude=72.8340,
        contact_number='+91 22 2285 2885',
        is_24_hours=True,
        address='Near Gateway of India, Apollo Bandar, Colaba, Mumbai'
    )
    SafetyPOI.objects.create(
        name='Marine Drive Police Station & Promenade Post',
        poi_type='POLICE',
        latitude=18.9435,
        longitude=72.8235,
        contact_number='+91 22 2281 2788',
        is_24_hours=True,
        address='Netaji Subhash Chandra Bose Road, Marine Drive, Mumbai'
    )
    SafetyPOI.objects.create(
        name='Bandra Police Station & Bandstand Patrol',
        poi_type='POLICE',
        latitude=19.0550,
        longitude=72.8300,
        contact_number='+91 22 2642 2222',
        is_24_hours=True,
        address='Hill Road, Bandra West, Mumbai'
    )
    SafetyPOI.objects.create(
        name='Juhu Beach Tourist Police Assistance Booth',
        poi_type='TOURIST_POLICE',
        latitude=19.0988,
        longitude=72.8264,
        contact_number='+91 22 2618 3535',
        is_24_hours=True,
        address='Juhu Tara Road, Juhu Beach Promenade, Mumbai'
    )
    SafetyPOI.objects.create(
        name='Bombay Hospital & Medical Research Centre',
        poi_type='HOSPITAL',
        latitude=18.9400,
        longitude=72.8290,
        contact_number='+91 22 2206 7676',
        is_24_hours=True,
        address='12, Marine Lines, Mumbai, Maharashtra 400020'
    )
    SafetyPOI.objects.create(
        name='Lilavati Hospital & Research Centre',
        poi_type='HOSPITAL',
        latitude=19.0515,
        longitude=72.8295,
        contact_number='+91 22 2675 1000',
        is_24_hours=True,
        address='A-791, Bandra Reclamation, Bandra West, Mumbai'
    )
    SafetyPOI.objects.create(
        name='Nanavati Max Super Speciality Hospital',
        poi_type='HOSPITAL',
        latitude=19.0970,
        longitude=72.8420,
        contact_number='+91 22 2626 7500',
        is_24_hours=True,
        address='SV Road, Vile Parle West, Near Juhu, Mumbai'
    )
    SafetyPOI.objects.create(
        name='Sir H. N. Reliance Foundation Hospital & Research Centre',
        poi_type='HOSPITAL',
        latitude=18.9575,
        longitude=72.8190,
        contact_number='+91 22 6130 5000',
        is_24_hours=True,
        address='Raja Rammohan Roy Road, Prarthana Samaj, Girgaon, Mumbai'
    )

    # =========================================================================
    # DELHI (NCR) SAFETY POIs
    # =========================================================================
    SafetyPOI.objects.create(
        name='Connaught Place Police Station & Tourist Desk',
        poi_type='POLICE',
        latitude=28.6315,
        longitude=77.2167,
        contact_number='+91 11 2336 4111',
        is_24_hours=True,
        address='Near Rajiv Chowk, Outer Circle, Connaught Place, New Delhi'
    )
    SafetyPOI.objects.create(
        name='Tilak Marg Police Station (India Gate & Kartavya Path)',
        poi_type='TOURIST_POLICE',
        latitude=28.6185,
        longitude=77.2380,
        contact_number='+91 11 2338 5222',
        is_24_hours=True,
        address='Tilak Marg, Near India Gate C-Hexagon, New Delhi'
    )
    SafetyPOI.objects.create(
        name='Kotwali Police Station (Red Fort & Chandni Chowk)',
        poi_type='POLICE',
        latitude=28.6562,
        longitude=77.2340,
        contact_number='+91 11 2327 4111',
        is_24_hours=True,
        address='Opposite Red Fort Main Gate, Chandni Chowk, Delhi'
    )
    SafetyPOI.objects.create(
        name='Mehrauli Police Station (Qutub Minar Complex)',
        poi_type='POLICE',
        latitude=28.5245,
        longitude=77.1855,
        contact_number='+91 11 2664 3000',
        is_24_hours=True,
        address='Mehrauli-Gurgaon Road, Near Qutub Minar, New Delhi'
    )
    SafetyPOI.objects.create(
        name='AIIMS Emergency Trauma Centre New Delhi',
        poi_type='HOSPITAL',
        latitude=28.5670,
        longitude=77.2100,
        contact_number='+91 11 2658 8500',
        is_24_hours=True,
        address='Sri Aurobindo Marg, Ansari Nagar East, New Delhi'
    )
    SafetyPOI.objects.create(
        name='Safdarjung Hospital 24x7 Emergency & Trauma Unit',
        poi_type='HOSPITAL',
        latitude=28.5705,
        longitude=77.2065,
        contact_number='+91 11 2616 5060',
        is_24_hours=True,
        address='Ring Road, Opposite AIIMS, New Delhi'
    )
    SafetyPOI.objects.create(
        name='Dr. Ram Manohar Lohia (RML) Hospital',
        poi_type='HOSPITAL',
        latitude=28.6250,
        longitude=77.2025,
        contact_number='+91 11 2336 5525',
        is_24_hours=True,
        address='Baba Kharak Singh Marg, Near CP, New Delhi'
    )
    SafetyPOI.objects.create(
        name='Max Super Speciality Hospital Saket',
        poi_type='HOSPITAL',
        latitude=28.5280,
        longitude=77.2130,
        contact_number='+91 11 2651 5050',
        is_24_hours=True,
        address='1, 2, Press Enclave Road, Saket, New Delhi'
    )

    # =========================================================================
    # NOIDA SAFETY POIs
    # =========================================================================
    SafetyPOI.objects.create(
        name='Noida Sector 20 Police Station & Pink Women Booth',
        poi_type='POLICE',
        latitude=28.5710,
        longitude=77.3250,
        contact_number='+91 120 252 2222',
        is_24_hours=True,
        address='Sector 20, Near Sector 18 Commercial Market, Noida'
    )
    SafetyPOI.objects.create(
        name='Noida Sector 39 Police Station & Metro Post',
        poi_type='POLICE',
        latitude=28.5620,
        longitude=77.3550,
        contact_number='+91 120 257 3939',
        is_24_hours=True,
        address='Sector 39, Near District Hospital, Noida'
    )
    SafetyPOI.objects.create(
        name='Expressway Police Station Sector 135',
        poi_type='POLICE',
        latitude=28.5020,
        longitude=77.4080,
        contact_number='+91 120 297 0100',
        is_24_hours=True,
        address='Noida-Greater Noida Expressway, Sector 135, Noida'
    )
    SafetyPOI.objects.create(
        name='Kailash Hospital & Heart Institute Noida',
        poi_type='HOSPITAL',
        latitude=28.5730,
        longitude=77.3260,
        contact_number='+91 120 244 4444',
        is_24_hours=True,
        address='H-33, Sector 27, Near Sector 18, Noida'
    )
    SafetyPOI.objects.create(
        name='Jaypee Hospital Multi-Speciality & Trauma Centre',
        poi_type='HOSPITAL',
        latitude=28.5130,
        longitude=77.3820,
        contact_number='+91 120 412 2222',
        is_24_hours=True,
        address='Sector 128, Wish Town, Noida'
    )
    SafetyPOI.objects.create(
        name='Fortis Hospital Sector 62 Noida',
        poi_type='HOSPITAL',
        latitude=28.6180,
        longitude=77.3720,
        contact_number='+91 120 430 0222',
        is_24_hours=True,
        address='B-22, Sector 62, Noida'
    )

    # =========================================================================
    # JAIPUR SAFETY POIs
    # =========================================================================
    SafetyPOI.objects.create(
        name='Manak Chowk Tourist Police Station (Hawa Mahal)',
        poi_type='TOURIST_POLICE',
        latitude=26.9240,
        longitude=75.8270,
        contact_number='+91 141 261 8862',
        is_24_hours=True,
        address='Badi Choupad, Pink City Heritage Precinct, Jaipur'
    )
    SafetyPOI.objects.create(
        name='Amer Fort Tourist Assistance Police Station',
        poi_type='TOURIST_POLICE',
        latitude=26.9855,
        longitude=75.8510,
        contact_number='+91 141 253 0144',
        is_24_hours=True,
        address='Near Amer Fort Maota Lake Gate, Amer, Jaipur'
    )
    SafetyPOI.objects.create(
        name='Nahargarh Fort Ridge Police Assistance Post',
        poi_type='POLICE',
        latitude=26.9380,
        longitude=75.8160,
        contact_number='+91 141 261 5444',
        is_24_hours=True,
        address='Nahargarh Fort Road, Aravalli Hills, Jaipur'
    )
    SafetyPOI.objects.create(
        name='Sawai Man Singh (SMS) Government Hospital & Trauma Centre',
        poi_type='HOSPITAL',
        latitude=26.9050,
        longitude=75.8180,
        contact_number='+91 141 251 8888',
        is_24_hours=True,
        address='JLN Marg, Ashok Nagar, Jaipur, Rajasthan'
    )
    SafetyPOI.objects.create(
        name='Fortis Escorts Hospital Malviya Nagar',
        poi_type='HOSPITAL',
        latitude=26.8520,
        longitude=75.8050,
        contact_number='+91 141 254 7000',
        is_24_hours=True,
        address='Jawahar Lal Nehru Marg, Malviya Nagar, Jaipur'
    )
    SafetyPOI.objects.create(
        name='Eternal Heart Care Centre (EHCC) Super Speciality',
        poi_type='HOSPITAL',
        latitude=26.8510,
        longitude=75.8120,
        contact_number='+91 141 395 7000',
        is_24_hours=True,
        address='3 A, Jagatpura Road, Near Jawahar Circle, Jaipur'
    )

    # =========================================================================
    # AGRA SAFETY POIs
    # =========================================================================
    SafetyPOI.objects.create(
        name='Taj Mahal East Gate Tourist Police Station',
        poi_type='TOURIST_POLICE',
        latitude=27.1750,
        longitude=78.0430,
        contact_number='+91 562 242 1204',
        is_24_hours=True,
        address='Taj East Gate Pedestrian Plaza, Tajganj, Agra'
    )
    SafetyPOI.objects.create(
        name='Rakabganj Police Station (Agra Fort Precinct)',
        poi_type='POLICE',
        latitude=27.1780,
        longitude=78.0190,
        contact_number='+91 562 242 0500',
        is_24_hours=True,
        address='Near Agra Fort Railway Station, Rakabganj, Agra'
    )
    SafetyPOI.objects.create(
        name='Tajganj Tourist Assistance Kiosk & Control',
        poi_type='TOURIST_POLICE',
        latitude=27.1680,
        longitude=78.0410,
        contact_number='+91 562 223 1111',
        is_24_hours=True,
        address='Fatehabad Road Tourism Corridor, Tajganj, Agra'
    )
    SafetyPOI.objects.create(
        name='S.N. Medical College & Emergency Hospital Agra',
        poi_type='HOSPITAL',
        latitude=27.1850,
        longitude=78.0150,
        contact_number='+91 562 226 0353',
        is_24_hours=True,
        address='Hospital Road, Moti Katra, Agra, Uttar Pradesh'
    )
    SafetyPOI.objects.create(
        name='Pushpanjali Hospital & Research Centre',
        poi_type='HOSPITAL',
        latitude=27.1980,
        longitude=78.0060,
        contact_number='+91 562 253 3333',
        is_24_hours=True,
        address='Delhi Gate, Prof. AL Srivastava Marg, Agra'
    )
    SafetyPOI.objects.create(
        name='Synergy Plus Hospital Multi-Speciality',
        poi_type='HOSPITAL',
        latitude=27.1550,
        longitude=78.0520,
        contact_number='+91 562 422 2222',
        is_24_hours=True,
        address='Fatehabad Road, Near Taj Nagari Phase 2, Agra'
    )

    # =========================================================================
    # GOA SAFETY POIs
    # =========================================================================
    SafetyPOI.objects.create(
        name='Calangute Tourist Police Station',
        poi_type='TOURIST_POLICE',
        latitude=15.5410,
        longitude=73.7620,
        contact_number='+91 832 227 7212',
        is_24_hours=True,
        address='Near Calangute Beach Circle, North Goa'
    )
    SafetyPOI.objects.create(
        name='Anjuna Coastal Police Outpost',
        poi_type='POLICE',
        latitude=15.5860,
        longitude=73.7430,
        contact_number='+91 832 227 3233',
        is_24_hours=True,
        address='Anjuna Beach Road, North Goa'
    )
    SafetyPOI.objects.create(
        name='Panaji Town Police Station',
        poi_type='POLICE',
        latitude=15.4980,
        longitude=73.8280,
        contact_number='+91 832 242 0808',
        is_24_hours=True,
        address='Church Square, Panaji, Central Goa'
    )
    SafetyPOI.objects.create(
        name='Old Goa Heritage Police Station',
        poi_type='POLICE',
        latitude=15.5010,
        longitude=73.9120,
        contact_number='+91 832 228 5227',
        is_24_hours=True,
        address='Near Basilica of Bom Jesus, Old Goa'
    )
    SafetyPOI.objects.create(
        name='Goa Medical College & Hospital (GMC) Bambolim',
        poi_type='HOSPITAL',
        latitude=15.4630,
        longitude=73.8560,
        contact_number='+91 832 245 8700',
        is_24_hours=True,
        address='NH 66, Bambolim, Central Goa'
    )
    SafetyPOI.objects.create(
        name='Manipal Hospital Dona Paula',
        poi_type='HOSPITAL',
        latitude=15.4610,
        longitude=73.8180,
        contact_number='+91 832 664 5555',
        is_24_hours=True,
        address='Dona Paula, Panaji, Goa'
    )
    SafetyPOI.objects.create(
        name='Vision Multispecialty Hospital Mapusa',
        poi_type='HOSPITAL',
        latitude=15.5920,
        longitude=73.8150,
        contact_number='+91 832 225 5555',
        is_24_hours=True,
        address='Morod, Mapusa, North Goa'
    )
    print("Created 32 Multi-City Safety POIs (Police Stations, Kiosks & 24x7 Hospitals).")

    # 7b. Multi-City PCR Patrol Vans & Responders
    # Mumbai
    ResponderUnit.objects.create(
        unit_code='PCR-MUM-COLABA-01',
        agency='POLICE',
        callsign='Patrol Colaba 01',
        officer_in_charge='Sub-Inspector R. Kadam',
        contact_number='+91 98200 11001',
        status='AVAILABLE',
        current_latitude=18.9225,
        current_longitude=72.8340,
        station_base_name='Colaba Police Station'
    )
    ResponderUnit.objects.create(
        unit_code='PCR-MUM-MD-03',
        agency='POLICE',
        callsign='Marine Drive Patrol 03',
        officer_in_charge='Head Constable S. Shinde',
        contact_number='+91 98200 11003',
        status='AVAILABLE',
        current_latitude=18.9430,
        current_longitude=72.8235,
        station_base_name='Marine Drive Police Station'
    )
    # Delhi
    ResponderUnit.objects.create(
        unit_code='PCR-DEL-IG-01',
        agency='POLICE',
        callsign='India Gate Command 01',
        officer_in_charge='Inspector K. Sharma',
        contact_number='+91 98110 22001',
        status='AVAILABLE',
        current_latitude=28.6130,
        current_longitude=77.2290,
        station_base_name='Central Vista Security Post'
    )
    ResponderUnit.objects.create(
        unit_code='PCR-DEL-CP-01',
        agency='POLICE',
        callsign='Connaught Place Patrol 01',
        officer_in_charge='Head Constable B. Singh',
        contact_number='+91 98110 22004',
        status='AVAILABLE',
        current_latitude=28.6315,
        current_longitude=77.2170,
        station_base_name='Connaught Place Police Station'
    )
    # Noida & Greater Noida
    ResponderUnit.objects.create(
        unit_code='PCR-NOI-PARI-01',
        agency='POLICE',
        callsign='Pari Chowk Rapid Patrol 01',
        officer_in_charge='Sub-Inspector R. Sharma',
        contact_number='+91 94544 01801',
        status='AVAILABLE',
        current_latitude=28.4735,
        current_longitude=77.5030,
        station_base_name='Knowledge Park Police Station'
    )
    ResponderUnit.objects.create(
        unit_code='PCR-NOI-KP-02',
        agency='POLICE',
        callsign='Knowledge Park QRT 02',
        officer_in_charge='Head Constable D. Singh',
        contact_number='+91 94544 01802',
        status='AVAILABLE',
        current_latitude=28.4650,
        current_longitude=77.4920,
        station_base_name='Knowledge Park Police Post'
    )
    ResponderUnit.objects.create(
        unit_code='PCR-NOI-EXP-03',
        agency='POLICE',
        callsign='Expressway Interceptor 03',
        officer_in_charge='Inspector V. Yadav',
        contact_number='+91 94544 01803',
        status='AVAILABLE',
        current_latitude=28.5020,
        current_longitude=77.4080,
        station_base_name='Sector 135 Expressway Police Station'
    )
    ResponderUnit.objects.create(
        unit_code='PCR-NOI-SEC18-01',
        agency='POLICE',
        callsign='UP112 PRV Sector 18',
        officer_in_charge='Sub-Inspector A. Bhati',
        contact_number='+91 94544 01804',
        status='AVAILABLE',
        current_latitude=28.5710,
        current_longitude=77.3220,
        station_base_name='Sector 20 Police Station'
    )
    # Jaipur
    ResponderUnit.objects.create(
        unit_code='PCR-JAI-HM-01',
        agency='TOURISM_POLICE',
        callsign='Jaipur Walled City PCR 01',
        officer_in_charge='Sub-Inspector G. Rathore',
        contact_number='+91 94140 14001',
        status='AVAILABLE',
        current_latitude=26.9240,
        current_longitude=75.8270,
        station_base_name='Manak Chowk Tourist Desk'
    )
    # Agra
    ResponderUnit.objects.create(
        unit_code='PCR-AGR-TAJ-01',
        agency='TOURISM_POLICE',
        callsign='Taj Mahal Security Alpha 01',
        officer_in_charge='Inspector V. K. Singh',
        contact_number='+91 94544 02701',
        status='AVAILABLE',
        current_latitude=27.1752,
        current_longitude=78.0425,
        station_base_name='Taj East Gate Police Base'
    )
    print("Created 10 Multi-City PCR Patrol Units.")

    # 8b. Multi-City Incidents
    # Mumbai
    Incident.objects.create(
        reporter=admin_user,
        reporter_name='Mumbai Tourist Control',
        reporter_phone='+91 22 2285 2885',
        category='NATURAL_HAZARD',
        severity='LOW',
        status='RESOLVED',
        title='High Tide Wave Advisory at Marine Drive Promenade',
        description='Monsoon swell caution issued along tetrapod seawall. Public advised to remain on main pedestrian sidewalk.',
        latitude=18.9430,
        longitude=72.8230,
        location_name='Marine Drive Promenade, Mumbai'
    )
    # Delhi
    Incident.objects.create(
        reporter=admin_user,
        reporter_name='Delhi Traffic & Tourism Unit',
        reporter_phone='+91 11 2346 9500',
        category='INFRASTRUCTURE',
        severity='LOW',
        status='IN_PROGRESS',
        title='Pedestrian Movement Regulated at Chandni Chowk',
        description='Crowd control barricades active for evening market festival.',
        latitude=28.6506,
        longitude=77.2303,
        location_name='Chandni Chowk Market Corridor, Old Delhi'
    )
    # Agra
    Incident.objects.create(
        reporter=admin_user,
        reporter_name='Tajganj Police Station',
        reporter_phone='+91 562 242 1204',
        category='OTHER',
        severity='LOW',
        status='RESOLVED',
        title='Unauthorized Drone Flyover Intercepted',
        description='Tourist drone brought down and operator counseled in Taj buffer zone.',
        latitude=27.1751,
        longitude=78.0421,
        location_name='Taj Mahal East Gate Buffer, Agra'
    )
    print("Created Multi-City Sample Incidents.")

    print("\n✅ Seed complete! Multi-city tourist safety network (Mumbai, Delhi, Noida, Jaipur, Agra, Goa) is active.")

    # 7. Create AI CCTV Camera Feeds
    VisionCameraFeed.objects.create(
        camera_code='CAM-CALANGUTE-01',
        location_name='Calangute Market Promenade Circle',
        latitude=15.5415,
        longitude=73.7575,
        max_safe_capacity=150,
        is_active=True
    )
    VisionCameraFeed.objects.create(
        camera_code='CAM-BAGA-BEACH-02',
        location_name='Baga Beach Main Boardwalk',
        latitude=15.5530,
        longitude=73.7515,
        max_safe_capacity=200,
        is_active=True
    )
    VisionCameraFeed.objects.create(
        camera_code='CAM-PANAJI-RIVER-03',
        location_name='Panaji Mandovi Riverfront Jetty',
        latitude=15.4990,
        longitude=73.8290,
        max_safe_capacity=100,
        is_active=True
    )
    print("Created 3 AI Vision Camera Feeds.")

    # 8. Create Sample Incident
    inc = Incident.objects.create(
        reporter=tourist1_user,
        reporter_name='Ananya Sen',
        reporter_phone='+91 98765 12345',
        category='THEFT',
        severity='HIGH',
        status='VERIFIED',
        title='Bag snatching reported near North Promenade',
        description='Two individuals on black motorcycle snatched a tourist handbag and sped towards coastal link road.',
        latitude=15.5010,
        longitude=73.8290,
        location_name='Near Mandovi Promenade Jetty #2',
        assigned_responder=r1
    )
    IncidentTimeline.objects.create(
        incident=inc,
        status='REPORTED',
        note='Report filed via mobile safety app by tourist.',
        actor=tourist1_user
    )
    IncidentTimeline.objects.create(
        incident=inc,
        status='VERIFIED',
        note='C2 Operator Sharma verified location and CCTV footage.',
        actor=officer
    )
    IncidentTimeline.objects.create(
        incident=inc,
        status='DISPATCHED',
        note='Assigned to PCR-PANJIM-01 for immediate intercept.',
        actor=officer
    )
    print("Created Sample Incident with complete audit timeline.")

    # 9. Create Sample Emergency Broadcast
    EmergencyBroadcast.objects.create(
        alert_type='SEVERE_WEATHER',
        title='High Wave & Rip Current Caution Advisory',
        message='Indian Coast Guard and Tourism Department advisory: High tide expected along North Goa shores between 18:00 and 22:00 hrs. Swimming prohibited beyond yellow buoys.',
        severity='WARNING',
        target_type='ALL_TOURISTS',
        issued_by=officer,
        is_active=True,
        starts_at=timezone.now(),
        expires_at=timezone.now() + timedelta(hours=24)
    )
    print("Created Sample Emergency Broadcast.")

    print("\n✅ Seed complete! All demo accounts, GIS zones, blackspots, and responders are ready.")

if __name__ == '__main__':
    populate()
