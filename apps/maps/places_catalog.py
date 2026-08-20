"""
VIGIL MULTI-CITY PLACE DIRECTORY & SAFETY INTELLIGENCE CATALOG
Provides comprehensive tourist landmarks, safety scorecards, PCR van telemetry,
active incidents, and restricted zone datasets across major Indian tourist hubs:
MUMBAI, DELHI, NOIDA, JAIPUR, AGRA, and GOA.
"""

from typing import List, Dict, Any, Optional
from common.utils import haversine_distance
from .models import SafetyPOI
from geofencing.models import GeoZone
from emergency.models import ResponderUnit
from incidents.models import Incident
from risk.models import Blackspot

# --- Cities Metadata & Safety Index ---
CITIES_METADATA = {
    "MUMBAI": {
        "city_code": "MUMBAI",
        "name": "Mumbai",
        "state": "Maharashtra",
        "tagline": "Financial Capital & Coastal Metropolis",
        "center_lat": 18.9400,
        "center_lng": 72.8300,
        "zoom": 12,
        "overall_safety_score": 89,
        "safety_level": "VERY SAFE",
        "police_control_room": "112 / 100",
        "tourist_helpline": "+91 22 2207 4333",
        "ems_ambulance": "108",
        "total_active_pcr_vans": 18,
        "total_restricted_zones": 3,
        "safety_summary": "Extensive 24x7 coastal police presence and continuous illumination along Queen's Necklace, Bandra, and Gateway sectors with high CCTV surveillance density."
    },
    "DELHI": {
        "city_code": "DELHI",
        "name": "Delhi (NCR)",
        "state": "National Capital Territory",
        "tagline": "National Capital & Historic Heritage Hub",
        "center_lat": 28.6139,
        "center_lng": 77.2090,
        "zoom": 12,
        "overall_safety_score": 83,
        "safety_level": "MONITORED",
        "police_control_room": "112 / +91 11 2346 9500",
        "tourist_helpline": "1800-11-1363 (Toll Free)",
        "ems_ambulance": "102 / 108",
        "total_active_pcr_vans": 24,
        "total_restricted_zones": 4,
        "safety_summary": "Designated High-Security Tourist Corridors across Kartavya Path, Connaught Place, and UNESCO heritage monuments with rapid response PCR dispatch."
    },
    "NOIDA": {
        "city_code": "NOIDA",
        "name": "Noida & Greater Noida",
        "state": "Uttar Pradesh (NCR)",
        "tagline": "Pari Chowk, Knowledge Park & High-Tech Urban Safety Grid",
        "center_lat": 28.4744,
        "center_lng": 77.5040,
        "zoom": 13,
        "overall_safety_score": 90,
        "safety_level": "VERY SAFE",
        "police_control_room": "112 (UP Emergency / Greater Noida Control)",
        "tourist_helpline": "+91 120 252 2222",
        "ems_ambulance": "108",
        "total_active_pcr_vans": 16,
        "total_restricted_zones": 2,
        "safety_summary": "Integrated Greater Noida & Noida urban surveillance corridor with continuous 24x7 Pari Chowk, Knowledge Park, and Expressway PRV rapid dispatch units."
    },
    "JAIPUR": {
        "city_code": "JAIPUR",
        "name": "Jaipur",
        "state": "Rajasthan",
        "tagline": "The Pink City & Royal Heritage Capital",
        "center_lat": 26.9200,
        "center_lng": 75.8200,
        "zoom": 13,
        "overall_safety_score": 91,
        "safety_level": "VERY SAFE",
        "police_control_room": "112 / +91 141 261 5444",
        "tourist_helpline": "+91 141 282 2845",
        "ems_ambulance": "108",
        "total_active_pcr_vans": 14,
        "total_restricted_zones": 2,
        "safety_summary": "Dedicated Rajasthan Tourist Police Force stationed at all major forts (Amer, Nahargarh, City Palace) with multi-lingual assistance and verified guide protocols."
    },
    "AGRA": {
        "city_code": "AGRA",
        "name": "Agra",
        "state": "Uttar Pradesh",
        "tagline": "World Heritage City of the Taj Mahal",
        "center_lat": 27.1800,
        "center_lng": 78.0200,
        "zoom": 13,
        "overall_safety_score": 93,
        "safety_level": "HIGH SECURITY",
        "police_control_room": "112 / +91 562 222 6666",
        "tourist_helpline": "+91 562 242 1204",
        "ems_ambulance": "108",
        "total_active_pcr_vans": 16,
        "total_restricted_zones": 3,
        "safety_summary": "Taj Trapezium High-Security Zone featuring multi-tier CISF and Tourist Police perimeters, 500m eco-friendly pedestrian safe corridor, and rapid trauma transit."
    },
    "GOA": {
        "city_code": "GOA",
        "name": "Goa",
        "state": "Goa",
        "tagline": "Coastal Safety, Beach Tourism & Heritage",
        "center_lat": 15.4989,
        "center_lng": 73.8278,
        "zoom": 12,
        "overall_safety_score": 94,
        "safety_level": "VERY SAFE",
        "police_control_room": "112 / +91 832 242 0808",
        "tourist_helpline": "+91 832 243 8750",
        "ems_ambulance": "108",
        "total_active_pcr_vans": 20,
        "total_restricted_zones": 4,
        "safety_summary": "Active coastal lifeguard watchtowers, 24x7 beach police patrol corridors, and PostGIS geofenced cliffhead safety perimeters."
    }
}


# --- Curated Landmark Directory with Deep Safety Profiles ---
LANDMARKS_CATALOG = [
    # ==========================================================================
    # MUMBAI LANDMARKS
    # ==========================================================================
    {
        "id": "MUM_GATEWAY",
        "name": "Gateway of India & Taj Mahal Palace",
        "city_code": "MUMBAI",
        "city_name": "Mumbai",
        "category": "HERITAGE",
        "category_display": "🏰 Iconic Waterfront Heritage",
        "latitude": 18.9220,
        "longitude": 72.8347,
        "address": "Apollo Bandar, Colaba, Mumbai, Maharashtra 400001",
        "safety_score": 95,
        "safety_level": "VERY SAFE",
        "lighting": "High-Intensity 24x7 Illumination",
        "crowd_level": "High Tourist Flow (Monitored)",
        "police_coverage": "24x7 Colaba Coastal Police & CISF Waterfront Post",
        "emergency_phone": "+91 22 2285 2885",
        "pcr_vans": [
            {"callsign": "Patrol Colaba 01", "unit_code": "PCR-MUM-COLABA-01", "officer": "SI R. Kadam", "contact": "+91 98200 11001", "status": "AVAILABLE", "distance_m": 180},
            {"callsign": "South Mumbai Quick Response", "unit_code": "PCR-MUM-QRT-02", "officer": "Insp. V. Patil", "contact": "+91 98200 11002", "status": "AVAILABLE", "distance_m": 420}
        ],
        "active_incidents": [],
        "restricted_zones": [
            {"name": "Gateway Jetty Restricted Water Perimeter", "zone_type": "RESTRICTED", "risk_level": "HIGH", "reason": "No unauthorized swimming or unlicensed boat boarding."}
        ],
        "nearby_hospitals": [
            {"name": "Bombay Hospital & Medical Research Centre", "distance_km": 2.2, "phone": "+91 22 2206 7676"},
            {"name": "St. George Government Hospital", "distance_km": 1.8, "phone": "+91 22 2262 0242"}
        ],
        "safety_tips": "Stay within the pedestrianized plaza. Avoid touts offering unverified boat excursions; use official MTDC ticket booths."
    },
    {
        "id": "MUM_MARINE_DRIVE",
        "name": "Marine Drive (Queen's Necklace)",
        "city_code": "MUMBAI",
        "city_name": "Mumbai",
        "category": "BEACH",
        "category_display": "🌊 Scenic Coastal Promenade",
        "latitude": 18.9430,
        "longitude": 72.8230,
        "address": "Netaji Subhash Chandra Bose Road, Mumbai, Maharashtra",
        "safety_score": 92,
        "safety_level": "VERY SAFE",
        "lighting": "Continuous High-Mast LED Lighting",
        "crowd_level": "Moderate to High Evening Promenade",
        "police_coverage": "Marine Drive Police Station & Mobile Bike Patrols",
        "emergency_phone": "+91 22 2281 2788",
        "pcr_vans": [
            {"callsign": "Marine Drive Van 03", "unit_code": "PCR-MUM-MD-03", "officer": "HC S. Shinde", "contact": "+91 98200 11003", "status": "AVAILABLE", "distance_m": 250}
        ],
        "active_incidents": [
            {"title": "High Tide Spray Warning", "severity": "LOW", "category": "NATURAL_HAZARD", "time": "Active Today", "advice": "Avoid sitting directly on seaside tetrapods during monsoon surge."}
        ],
        "restricted_zones": [
            {"name": "Marine Drive Tetrapod Seawall Buffer", "zone_type": "HIGH_RISK", "risk_level": "MEDIUM", "reason": "Steep slippery rocks; climbing onto tetrapods is strictly prohibited."}
        ],
        "nearby_hospitals": [
            {"name": "Saifee Hospital Charni Road", "distance_km": 0.8, "phone": "+91 22 6757 0111"}
        ],
        "safety_tips": "Well-lit and exceptionally safe for late evening walks. Use marked zebra crossings when crossing the 6-lane boulevard."
    },
    {
        "id": "MUM_JUHU",
        "name": "Juhu Beach & Sunset Promenade",
        "city_code": "MUMBAI",
        "city_name": "Mumbai",
        "category": "BEACH",
        "category_display": "🏖️ Popular Beach & Food Street",
        "latitude": 19.0988,
        "longitude": 72.8264,
        "address": "Juhu Tara Road, Juhu, Mumbai, Maharashtra 400049",
        "safety_score": 88,
        "safety_level": "SAFE",
        "lighting": "Well-Lit Boardwalk & Food Pavilions",
        "crowd_level": "High Evening Density",
        "police_coverage": "Juhu Beach Tourist Assistance Booth & Lifeguards",
        "emergency_phone": "+91 22 2618 4344",
        "pcr_vans": [
            {"callsign": "Juhu Beach Coastal 01", "unit_code": "PCR-MUM-JUHU-01", "officer": "SI M. More", "contact": "+91 98200 11004", "status": "AVAILABLE", "distance_m": 310}
        ],
        "active_incidents": [],
        "restricted_zones": [
            {"name": "Juhu Deep Water Current Zone", "zone_type": "RESTRICTED", "risk_level": "CRITICAL", "reason": "Dangerous undertow during high tide. Obey red flags."}
        ],
        "nearby_hospitals": [
            {"name": "Nanavati Max Super Speciality Hospital", "distance_km": 1.9, "phone": "+91 22 2626 7500"}
        ],
        "safety_tips": "Observe lifeguard warning flags before entering water. Keep personal belongings secure in crowded chaat stall areas."
    },
    {
        "id": "MUM_BANDRA_FORT",
        "name": "Bandra Bandstand & Castella de Aguada",
        "city_code": "MUMBAI",
        "city_name": "Mumbai",
        "category": "HERITAGE",
        "category_display": "🏰 Coastal Fort & Walkway",
        "latitude": 19.0430,
        "longitude": 72.8190,
        "address": "Bandstand Promenade, Bandra West, Mumbai 400050",
        "safety_score": 87,
        "safety_level": "SAFE",
        "lighting": "Moderate Coastal Illumination",
        "crowd_level": "Moderate Tourist Flow",
        "police_coverage": "Bandra West Police Patrol Unit",
        "emergency_phone": "+91 22 2642 3444",
        "pcr_vans": [
            {"callsign": "Bandra Sector Van 02", "unit_code": "PCR-MUM-BND-02", "officer": "HC D. Sawant", "contact": "+91 98200 11005", "status": "AVAILABLE", "distance_m": 290}
        ],
        "active_incidents": [],
        "restricted_zones": [
            {"name": "Bandstand Rocky Slip Perimeter", "zone_type": "RESTRICTED", "risk_level": "HIGH", "reason": "Slippery rocky shore during high tide; safety railings in place."}
        ],
        "nearby_hospitals": [
            {"name": "Lilavati Hospital & Research Centre", "distance_km": 1.4, "phone": "+91 22 2675 1000"}
        ],
        "safety_tips": "Do not venture past warning barricades onto wet coastal boulders during turbulent sea conditions."
    },
    {
        "id": "MUM_COLABA_CAUSEWAY",
        "name": "Colaba Causeway Cultural Market",
        "city_code": "MUMBAI",
        "city_name": "Mumbai",
        "category": "MARKET",
        "category_display": "🛍️ Vibrant Tourist Bazaar",
        "latitude": 18.9150,
        "longitude": 72.8270,
        "address": "Shahid Bhagat Singh Road, Colaba, Mumbai",
        "safety_score": 86,
        "safety_level": "SAFE",
        "lighting": "Well-Lit Commercial Arcade",
        "crowd_level": "High Shopping Density",
        "police_coverage": "Colaba Police Foot Patrols & Fixed Checkpost",
        "emergency_phone": "+91 22 2285 2885",
        "pcr_vans": [
            {"callsign": "Colaba Market Patrol", "unit_code": "PCR-MUM-COLABA-02", "officer": "SI A. Mane", "contact": "+91 98200 11006", "status": "AVAILABLE", "distance_m": 120}
        ],
        "active_incidents": [
            {"title": "Crowded Sidewalk Advisory", "severity": "LOW", "category": "CROWD_SURGE", "time": "Active", "advice": "Keep backpacks zipped and wallets in front pockets."}
        ],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "INHS Asvini Naval Hospital", "distance_km": 1.5, "phone": "+91 22 2215 1666"}
        ],
        "safety_tips": "Negotiate taxi fares using official meters or ride-hailing apps. Keep valuables secure."
    },

    # ==========================================================================
    # DELHI LANDMARKS
    # ==========================================================================
    {
        "id": "DEL_INDIA_GATE",
        "name": "India Gate & Kartavya Path",
        "city_code": "DELHI",
        "city_name": "Delhi (NCR)",
        "category": "HERITAGE",
        "category_display": "🏛️ National Memorial & Central Vista",
        "latitude": 28.6129,
        "longitude": 77.2295,
        "address": "Rajpath, India Gate, New Delhi, Delhi 110001",
        "safety_score": 96,
        "safety_level": "VERY HIGH SECURITY",
        "lighting": "Maximum Architectural & Street Illumination",
        "crowd_level": "High Evening Density (Extensive Security)",
        "police_coverage": "24x7 Delhi Police & Central Security Paramilitary Posts",
        "emergency_phone": "+91 11 2338 2222",
        "pcr_vans": [
            {"callsign": "India Gate Command 01", "unit_code": "PCR-DEL-IG-01", "officer": "Insp. K. Sharma", "contact": "+91 98110 22001", "status": "AVAILABLE", "distance_m": 150},
            {"callsign": "Central Vista Patrol 02", "unit_code": "PCR-DEL-CV-02", "officer": "SI R. Verma", "contact": "+91 98110 22002", "status": "AVAILABLE", "distance_m": 350}
        ],
        "active_incidents": [],
        "restricted_zones": [
            {"name": "Amar Jawan Jyoti High-Security Buffer", "zone_type": "RESTRICTED", "risk_level": "LOW", "reason": "Ceremonial military zone; strictly pedestrianized and bag-checked."}
        ],
        "nearby_hospitals": [
            {"name": "Dr. Ram Manohar Lohia Hospital (RML)", "distance_km": 2.8, "phone": "+91 11 2336 5525"},
            {"name": "AIIMS Trauma Centre New Delhi", "distance_km": 4.5, "phone": "+91 11 2658 8500"}
        ],
        "safety_tips": "Strictly monitored sector. Free drinking water kiosks and clean tourist facilities available throughout Kartavya Path."
    },
    {
        "id": "DEL_RED_FORT",
        "name": "Red Fort (Lal Qila Heritage Complex)",
        "city_code": "DELHI",
        "city_name": "Delhi (NCR)",
        "category": "HERITAGE",
        "category_display": "🏰 UNESCO World Heritage Monument",
        "latitude": 28.6562,
        "longitude": 77.2410,
        "address": "Netaji Subhash Marg, Lal Qila, Chandni Chowk, Old Delhi 110006",
        "safety_score": 91,
        "safety_level": "VERY SAFE",
        "lighting": "Well-Lit Monument Enclosure",
        "crowd_level": "High Daytime Tourist Influx",
        "police_coverage": "CISF Monument Protection & Kotwali Tourist Police",
        "emergency_phone": "+91 11 2327 4555",
        "pcr_vans": [
            {"callsign": "Lal Qila Rapid Unit 01", "unit_code": "PCR-DEL-LQ-01", "officer": "SI M. Yadav", "contact": "+91 98110 22003", "status": "AVAILABLE", "distance_m": 200}
        ],
        "active_incidents": [],
        "restricted_zones": [
            {"name": "ASI Archaeological Preservation Perimeter", "zone_type": "RESTRICTED", "risk_level": "MEDIUM", "reason": "No entry past ASI barricades into historic ramparts."}
        ],
        "nearby_hospitals": [
            {"name": "Lok Nayak Jai Prakash Hospital (LNJP)", "distance_km": 1.6, "phone": "+91 11 2323 3000"}
        ],
        "safety_tips": "Book entrance tickets online via the official ASI portal to bypass long lines. Metro connectivity via Lal Qila Station."
    },
    {
        "id": "DEL_CP",
        "name": "Connaught Place (CP Central Ring)",
        "city_code": "DELHI",
        "city_name": "Delhi (NCR)",
        "category": "MARKET",
        "category_display": "🛍️ Premier Shopping & Dining Hub",
        "latitude": 28.6315,
        "longitude": 77.2167,
        "address": "Connaught Place, New Delhi, Delhi 110001",
        "safety_score": 90,
        "safety_level": "SAFE",
        "lighting": "High Urban Commercial Illumination",
        "crowd_level": "High Multi-Block Commercial Flow",
        "police_coverage": "Connaught Place Police Station & Tourist PCR Booths",
        "emergency_phone": "+91 11 2336 4111",
        "pcr_vans": [
            {"callsign": "CP Inner Circle Patrol", "unit_code": "PCR-DEL-CP-01", "officer": "HC B. Singh", "contact": "+91 98110 22004", "status": "AVAILABLE", "distance_m": 90}
        ],
        "active_incidents": [],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "Lady Hardinge Medical College & Hospital", "distance_km": 0.9, "phone": "+91 11 2336 3728"}
        ],
        "safety_tips": "Palika Bazaar underground and Inner Circle radial roads have active CCTV monitoring. Rajiv Chowk Metro station is directly below."
    },
    {
        "id": "DEL_QUTUB_MINAR",
        "name": "Qutub Minar & Mehrauli Heritage Complex",
        "city_code": "DELHI",
        "city_name": "Delhi (NCR)",
        "category": "HERITAGE",
        "category_display": "🏛️ UNESCO World Heritage Minaret",
        "latitude": 28.5244,
        "longitude": 77.1855,
        "address": "Seth Sarai, Mehrauli, New Delhi, Delhi 110030",
        "safety_score": 92,
        "safety_level": "VERY SAFE",
        "lighting": "Architectural Night Illumination",
        "crowd_level": "Moderate Daytime Influx",
        "police_coverage": "Mehrauli Police Station & ASI Security Desk",
        "emergency_phone": "+91 11 2664 2222",
        "pcr_vans": [
            {"callsign": "South Heritage Patrol", "unit_code": "PCR-DEL-QM-01", "officer": "SI P. Tanwar", "contact": "+91 98110 22005", "status": "AVAILABLE", "distance_m": 300}
        ],
        "active_incidents": [],
        "restricted_zones": [
            {"name": "Mehrauli Dense Forest Edge Buffer", "zone_type": "HIGH_RISK", "risk_level": "MEDIUM", "reason": "Unlit wooded perimeter after 20:00. Stay on paved illuminated tracks."}
        ],
        "nearby_hospitals": [
            {"name": "Max Super Speciality Hospital Saket", "distance_km": 2.1, "phone": "+91 11 2651 5050"}
        ],
        "safety_tips": "The monument complex is exceptionally well-maintained. Sound & Light show evenings are fully security-monitored."
    },
    {
        "id": "DEL_LOTUS_TEMPLE",
        "name": "Lotus Temple (Bahá'í House of Worship)",
        "city_code": "DELHI",
        "city_name": "Delhi (NCR)",
        "category": "HERITAGE",
        "category_display": "🌸 World Heritage Spiritual Sanctuary",
        "latitude": 28.5535,
        "longitude": 77.2588,
        "address": "Lotus Temple Rd, Bahapur, Kalkaji, New Delhi 110019",
        "safety_score": 94,
        "safety_level": "VERY SAFE",
        "lighting": "Gleaming Marble Night Illumination",
        "crowd_level": "High Visitor Flow with Strict Silence Protocol",
        "police_coverage": "Kalkaji Police Station & Private Temple Guards",
        "emergency_phone": "+91 11 2644 4444",
        "pcr_vans": [
            {"callsign": "Kalkaji Sector Van 02", "unit_code": "PCR-DEL-LT-02", "officer": "HC S. Gujjar", "contact": "+91 98110 22006", "status": "AVAILABLE", "distance_m": 220}
        ],
        "active_incidents": [],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "Apollo Spectra Hospital Nehru Enclave", "distance_km": 1.2, "phone": "+91 11 4050 4400"}
        ],
        "safety_tips": "Bags undergo electronic screening at entrance. Shoes must be deposited at the free tokenized cloakroom."
    },

    # ==========================================================================
    # NOIDA & GREATER NOIDA LANDMARKS
    # ==========================================================================
    {
        "id": "NOIDA_PARI_CHOWK",
        "name": "Pari Chowk & Knowledge Park Safety Hub",
        "city_code": "NOIDA",
        "city_name": "Greater Noida",
        "category": "HERITAGE",
        "category_display": "🏛️ Landmark Transit & Knowledge Park Hub",
        "latitude": 28.4744,
        "longitude": 77.5040,
        "address": "Pari Chowk, Knowledge Park II, Greater Noida, Uttar Pradesh 201310",
        "safety_score": 94,
        "safety_level": "VERY SAFE",
        "lighting": "High-Mast 24x7 LED Illumination",
        "crowd_level": "Moderate to High Educational & Transit Flow",
        "police_coverage": "24x7 Knowledge Park Police Post & Pari Chowk Integrated Control Booth",
        "emergency_phone": "112 / +91 120 232 0100",
        "pcr_vans": [
            {"callsign": "Pari Chowk Rapid Patrol 01", "unit_code": "PCR-NOI-PARI-01", "officer": "SI R. Sharma", "contact": "+91 94544 01801", "status": "AVAILABLE", "distance_m": 140},
            {"callsign": "Knowledge Park QRT 02", "unit_code": "PCR-NOI-KP-02", "officer": "HC D. Singh", "contact": "+91 94544 01802", "status": "AVAILABLE", "distance_m": 350}
        ],
        "active_incidents": [],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "Sharda Hospital & Trauma Centre (KP III)", "distance_km": 1.2, "phone": "+91 120 232 9999"},
            {"name": "Kailash Hospital Greater Noida", "distance_km": 0.8, "phone": "+91 120 232 7777"}
        ],
        "safety_tips": "Major transit hub with direct Aqua Line Metro station (Pari Chowk). Continuous police booth assistance available."
    },
    {
        "id": "NOIDA_EXP_SEC135",
        "name": "Noida-Greater Noida Expressway Hub (Sector 135)",
        "city_code": "NOIDA",
        "city_name": "Noida",
        "category": "MARKET",
        "category_display": "🏢 Expressway Commercial Corridor",
        "latitude": 28.5020,
        "longitude": 77.4080,
        "address": "Noida Expressway, Sector 135, Noida, Uttar Pradesh",
        "safety_score": 92,
        "safety_level": "VERY SAFE",
        "lighting": "Continuous Highway LED Illumination",
        "crowd_level": "Corporate & Tech Transit",
        "police_coverage": "Sector 135 Expressway Police Station & Mobile Highway Interceptors",
        "emergency_phone": "112 / +91 120 297 0100",
        "pcr_vans": [
            {"callsign": "Expressway Interceptor 03", "unit_code": "PCR-NOI-EXP-03", "officer": "Insp. V. Yadav", "contact": "+91 94544 01803", "status": "AVAILABLE", "distance_m": 280}
        ],
        "active_incidents": [],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "Jaypee Hospital Multi-Speciality (Sector 128)", "distance_km": 2.6, "phone": "+91 120 412 2222"},
            {"name": "Felix Hospital (Sector 137)", "distance_km": 1.9, "phone": "+91 120 398 8888"}
        ],
        "safety_tips": "Highway corridor with dedicated speed-monitoring cameras and 24x7 emergency tow/medical response."
    },
    {
        "id": "NOIDA_BUDDH_CIRCUIT",
        "name": "Buddh International Circuit & Sports City",
        "city_code": "NOIDA",
        "city_name": "Greater Noida",
        "category": "HERITAGE",
        "category_display": "🏎️ World-Class Motorsports & Sports Arena",
        "latitude": 28.3490,
        "longitude": 77.5340,
        "address": "Jaypee Sports City, Yamuna Expressway, Greater Noida 203201",
        "safety_score": 95,
        "safety_level": "MAXIMUM SECURITY",
        "lighting": "Full Arena High-Beam Illumination",
        "crowd_level": "Event Specific (Regulated)",
        "police_coverage": "Dankaur & Yamuna Expressway Highway Task Force",
        "emergency_phone": "112 / +91 120 234 1000",
        "pcr_vans": [
            {"callsign": "Yamuna Expressway PRV 08", "unit_code": "PCR-NOI-YEX-08", "officer": "SI P. Mishra", "contact": "+91 94544 01808", "status": "AVAILABLE", "distance_m": 420}
        ],
        "active_incidents": [],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "Yatharth Super Speciality Hospital Greater Noida", "distance_km": 6.5, "phone": "+91 120 239 9999"}
        ],
        "safety_tips": "Controlled access venue with multi-tier perimeter security. Accessible via Yamuna Expressway."
    },
    {
        "id": "NOIDA_SEC_18",
        "name": "Noida Sector 18 Commercial Hub & Atta Market",
        "city_code": "NOIDA",
        "city_name": "Noida",
        "category": "MARKET",
        "category_display": "🛍️ Vibrant Retail & Dining Sector",
        "latitude": 28.5708,
        "longitude": 77.3216,
        "address": "Sector 18, Noida, Uttar Pradesh 201301",
        "safety_score": 89,
        "safety_level": "SAFE",
        "lighting": "High Commercial Illumination",
        "crowd_level": "High Evening Density",
        "police_coverage": "Sector 20 Police Station & Dedicated Pink Police Outpost",
        "emergency_phone": "112 / +91 120 252 2222",
        "pcr_vans": [
            {"callsign": "UP112 PRV Sector 18", "unit_code": "PCR-NOI-SEC18-01", "officer": "SI A. Bhati", "contact": "+91 94544 01801", "status": "AVAILABLE", "distance_m": 110}
        ],
        "active_incidents": [],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "Kailash Hospital & Heart Institute", "distance_km": 1.1, "phone": "+91 120 244 4444"}
        ],
        "safety_tips": "Sector 18 has multi-level parking with round-the-clock CCTV. Direct access via Sector 18 Wave Metro."
    },
    {
        "id": "NOIDA_DLF_MALL",
        "name": "DLF Mall of India & Gardens Galleria",
        "city_code": "NOIDA",
        "city_name": "Noida",
        "category": "MARKET",
        "category_display": "🏢 Mega Entertainment & Retail Complex",
        "latitude": 28.5675,
        "longitude": 77.3210,
        "address": "Plot No - M 03, Sector 18, Noida 201301",
        "safety_score": 96,
        "safety_level": "VERY HIGH SECURITY",
        "lighting": "Full Architectural & Facility Illumination",
        "crowd_level": "High Shopping & Cinema Traffic",
        "police_coverage": "24x7 Mall Security & Sector 20 Mobile PCR",
        "emergency_phone": "+91 120 620 9971",
        "pcr_vans": [
            {"callsign": "Noida City Center PRV", "unit_code": "PCR-NOI-MALL-02", "officer": "HC N. Tyagi", "contact": "+91 94544 01802", "status": "AVAILABLE", "distance_m": 160}
        ],
        "active_incidents": [],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "Max Multi Speciality Hospital Noida", "distance_km": 1.8, "phone": "+91 120 662 9999"}
        ],
        "safety_tips": "Complete indoor security protocol with metal detectors and high-density security guards across all floors."
    },
    {
        "id": "NOIDA_OKHLA_BIRD",
        "name": "Okhla Bird Sanctuary & Riverfront Walk",
        "city_code": "NOIDA",
        "city_name": "Noida",
        "category": "PARK",
        "category_display": "🌿 Eco Wetland & Nature Trail",
        "latitude": 28.5630,
        "longitude": 77.3120,
        "address": "Noida-Greater Noida Expressway, Sector 95, Noida",
        "safety_score": 84,
        "safety_level": "SAFE",
        "lighting": "Daytime Natural / Perimeter Solar Lights",
        "crowd_level": "Low to Moderate Morning Walkers",
        "police_coverage": "Forest Range Security & Highway Patrol",
        "emergency_phone": "+91 120 241 1234",
        "pcr_vans": [
            {"callsign": "Expressway PRV 04", "unit_code": "PCR-NOI-EXP-04", "officer": "SI R. Nagar", "contact": "+91 94544 01803", "status": "AVAILABLE", "distance_m": 480}
        ],
        "active_incidents": [],
        "restricted_zones": [
            {"name": "Yamuna Riverfront Marshland Perimeter", "zone_type": "RESTRICTED", "risk_level": "HIGH", "reason": "Deep mud and sudden water level rise. Stay on elevated wooden boardwalks."}
        ],
        "nearby_hospitals": [
            {"name": "Jaypee Hospital Expressway", "distance_km": 4.2, "phone": "+91 120 412 2222"}
        ],
        "safety_tips": "Sanctuary gates close at sunset (17:30). Direct entry adjacent to Okhla Bird Sanctuary Metro Station (Magenta Line)."
    },

    # ==========================================================================
    # JAIPUR LANDMARKS
    # ==========================================================================
    {
        "id": "JAI_HAWA_MAHAL",
        "name": "Hawa Mahal (Palace of Winds)",
        "city_code": "JAIPUR",
        "city_name": "Jaipur",
        "category": "HERITAGE",
        "category_display": "🏰 Iconic Pink Sandstone Palace",
        "latitude": 26.9239,
        "longitude": 75.8267,
        "address": "Hawa Mahal Rd, Badi Choupad, J.D.A. Market, Jaipur, Rajasthan 302002",
        "safety_score": 93,
        "safety_level": "VERY SAFE",
        "lighting": "Spectacular Heritage Façade Night Lighting",
        "crowd_level": "High Daytime & Evening Tourist Influx",
        "police_coverage": "Manak Chowk Tourist Police Station & Dedicated Helpdesk",
        "emergency_phone": "+91 141 261 8862",
        "pcr_vans": [
            {"callsign": "Jaipur Walled City PCR 01", "unit_code": "PCR-JAI-HM-01", "officer": "SI G. Rathore", "contact": "+91 94140 14001", "status": "AVAILABLE", "distance_m": 120}
        ],
        "active_incidents": [],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "Sawai Man Singh Hospital (SMS Medical College)", "distance_km": 2.4, "phone": "+91 141 251 8888"}
        ],
        "safety_tips": "Tourist Police assistance booth right across Badi Choupad. Only engage licensed RTDC tourist guides with verified badges."
    },
    {
        "id": "JAI_AMER_FORT",
        "name": "Amer Fort (Amber Palace & Maota Lake)",
        "city_code": "JAIPUR",
        "city_name": "Jaipur",
        "category": "HERITAGE",
        "category_display": "🏰 Hilltop Royal Citadel & Fort",
        "latitude": 26.9855,
        "longitude": 75.8513,
        "address": "Devisinghpura, Amer, Jaipur, Rajasthan 302001",
        "safety_score": 92,
        "safety_level": "VERY SAFE",
        "lighting": "Grand Citadel Evening Lighting & Sound Show",
        "crowd_level": "High Daytime Visitor Footfall",
        "police_coverage": "Amer Tourist Police Checkpost & Elephant Gate Guards",
        "emergency_phone": "+91 141 253 0264",
        "pcr_vans": [
            {"callsign": "Amer Heritage Quick Response", "unit_code": "PCR-JAI-AMER-02", "officer": "Insp. H. Shekhawat", "contact": "+91 94140 14002", "status": "AVAILABLE", "distance_m": 190}
        ],
        "active_incidents": [],
        "restricted_zones": [
            {"name": "Amer Outer Ramparts Cliffdrop Zone", "zone_type": "HIGH_RISK", "risk_level": "HIGH", "reason": "Steep unbarricaded battlements. Stick to designated paved corridors."}
        ],
        "nearby_hospitals": [
            {"name": "Amer Community Health Centre", "distance_km": 0.8, "phone": "+91 141 253 0108"}
        ],
        "safety_tips": "Electric golf carts available for seniors from Maota Lake to Suraj Pol entrance. Carry water bottles during daytime ascent."
    },
    {
        "id": "JAI_CITY_PALACE",
        "name": "City Palace & Jantar Mantar Observatory",
        "city_code": "JAIPUR",
        "city_name": "Jaipur",
        "category": "HERITAGE",
        "category_display": "👑 Royal Palace & Astronomical Observatory",
        "latitude": 26.9258,
        "longitude": 75.8236,
        "address": "Gangori Bazaar, J.D.A. Market, Pink City, Jaipur",
        "safety_score": 95,
        "safety_level": "VERY SAFE",
        "lighting": "Illuminated Palace Courtyards",
        "crowd_level": "High Flow with Guided Heritage Groups",
        "police_coverage": "Palace Security Wing & Pink City Patrols",
        "emergency_phone": "+91 141 408 8888",
        "pcr_vans": [
            {"callsign": "City Palace Patrol 03", "unit_code": "PCR-JAI-CP-03", "officer": "HC K. Meena", "contact": "+91 94140 14003", "status": "AVAILABLE", "distance_m": 140}
        ],
        "active_incidents": [],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "Santokba Durlabhji Memorial Hospital", "distance_km": 3.8, "phone": "+91 141 256 6251"}
        ],
        "safety_tips": "Audio guides in 8 languages available at the entrance. Photography allowed in outer courtyards."
    },
    {
        "id": "JAI_NAHARGARH",
        "name": "Nahargarh Fort & Hilltop Viewpoint",
        "city_code": "JAIPUR",
        "city_name": "Jaipur",
        "category": "HERITAGE",
        "category_display": "🏰 Panoramic Aravalli Fortress",
        "latitude": 26.9373,
        "longitude": 75.8155,
        "address": "Krishna Nagar, Brahampuri, Jaipur, Rajasthan 302002",
        "safety_score": 86,
        "safety_level": "SAFE",
        "lighting": "Moderate Hilltop Lighting",
        "crowd_level": "Popular Sunset Viewers",
        "police_coverage": "Nahargarh Hill Patrol & RTDC Gate Security",
        "emergency_phone": "+91 141 282 2845",
        "pcr_vans": [
            {"callsign": "Aravalli Ridge Patrol", "unit_code": "PCR-JAI-NAH-04", "officer": "SI D. Choudhary", "contact": "+91 94140 14004", "status": "AVAILABLE", "distance_m": 380}
        ],
        "active_incidents": [],
        "restricted_zones": [
            {"name": "Nahargarh Steep Cliff Edge", "zone_type": "RESTRICTED", "risk_level": "CRITICAL", "reason": "Unprotected sheer vertical drops along the outer wall. Do not sit on outer edge."}
        ],
        "nearby_hospitals": [
            {"name": "Kanwatia Government Hospital", "distance_km": 4.1, "phone": "+91 141 228 0108"}
        ],
        "safety_tips": "Use the paved vehicular road. Descend before complete darkness if traveling on two-wheelers."
    },

    # ==========================================================================
    # AGRA LANDMARKS
    # ==========================================================================
    {
        "id": "AGR_TAJ_MAHAL",
        "name": "Taj Mahal (East Gate & Complex)",
        "city_code": "AGRA",
        "city_name": "Agra",
        "category": "HERITAGE",
        "category_display": "🕌 UNESCO Wonder of the World",
        "latitude": 27.1751,
        "longitude": 78.0421,
        "address": "Dharmapuri, Forest Colony, Tajganj, Agra, Uttar Pradesh 282001",
        "safety_score": 97,
        "safety_level": "MAXIMUM SECURITY",
        "lighting": "Pristine Architectural & Perimeter Illumination",
        "crowd_level": "High International & Domestic Tourist Flow",
        "police_coverage": "CISF Elite Security & 24x7 Tajganj Tourist Police Station",
        "emergency_phone": "+91 562 242 1204",
        "pcr_vans": [
            {"callsign": "Taj Mahal Security Alpha 01", "unit_code": "PCR-AGR-TAJ-01", "officer": "Insp. V. K. Singh", "contact": "+91 94544 02701", "status": "AVAILABLE", "distance_m": 80},
            {"callsign": "Tajganj Tourist PRV 02", "unit_code": "PCR-AGR-TAJ-02", "officer": "SI P. Mishra", "contact": "+91 94544 02702", "status": "AVAILABLE", "distance_m": 220}
        ],
        "active_incidents": [],
        "restricted_zones": [
            {"name": "Taj 500m Eco-Vehicle Exclusion Zone", "zone_type": "SAFE_HAVEN", "risk_level": "LOW", "reason": "No combustion vehicles permitted; electric battery golf carts operate freely."},
            {"name": "Yamuna River Bank Security Buffer", "zone_type": "RESTRICTED", "risk_level": "HIGH", "reason": "High-security barrier on the rear Yamuna riverfront."}
        ],
        "nearby_hospitals": [
            {"name": "S.N. Medical College & Hospital Agra", "distance_km": 3.2, "phone": "+91 562 226 0353"},
            {"name": "Pushpanjali Hospital & Research Centre", "distance_km": 2.8, "phone": "+91 562 403 4444"}
        ],
        "safety_tips": "Only buy tickets from the official ASI ticket counters or website. Free shoe covers and water provided with high-value tickets."
    },
    {
        "id": "AGR_AGRA_FORT",
        "name": "Agra Fort (Red Sandstone Citadel)",
        "city_code": "AGRA",
        "city_name": "Agra",
        "category": "HERITAGE",
        "category_display": "🏰 UNESCO World Heritage Fortress",
        "latitude": 27.1795,
        "longitude": 78.0211,
        "address": "Agra Fort, Rakabganj, Agra, Uttar Pradesh 282003",
        "safety_score": 94,
        "safety_level": "VERY SAFE",
        "lighting": "Full Heritage Security Illumination",
        "crowd_level": "High Daytime Visitor Footfall",
        "police_coverage": "Military Area & Agra Tourist Police Wing",
        "emergency_phone": "+91 562 242 0005",
        "pcr_vans": [
            {"callsign": "Agra Fort Rapid Response", "unit_code": "PCR-AGR-FORT-01", "officer": "SI R. K. Tomar", "contact": "+91 94544 02703", "status": "AVAILABLE", "distance_m": 150}
        ],
        "active_incidents": [],
        "restricted_zones": [
            {"name": "Indian Army Garrison Perimeter", "zone_type": "RESTRICTED", "risk_level": "HIGH", "reason": "Portion of the fort is an active military station; respect signposted restricted arches."}
        ],
        "nearby_hospitals": [
            {"name": "Military Hospital Agra", "distance_km": 1.4, "phone": "+91 562 222 6100"}
        ],
        "safety_tips": "Ample shade inside the Diwan-i-Am and Diwan-i-Khas courtyards. Combined Agra heritage day passes accepted."
    },
    {
        "id": "AGR_MEHTAB_BAGH",
        "name": "Mehtab Bagh (Moonlight Garden Sunset View)",
        "city_code": "AGRA",
        "city_name": "Agra",
        "category": "PARK",
        "category_display": "🌿 Charbagh Riverfront Garden",
        "latitude": 27.1800,
        "longitude": 78.0440,
        "address": "Dharmapuri, Forest Colony, Nagla Devjit, Agra 282001",
        "safety_score": 90,
        "safety_level": "SAFE",
        "lighting": "Sunset Monitored Illumination",
        "crowd_level": "Moderate Sunset Photography Flow",
        "police_coverage": "ASI Guard Desk & River Patrol Post",
        "emergency_phone": "+91 562 242 1204",
        "pcr_vans": [
            {"callsign": "Yamuna River Bank PRV", "unit_code": "PCR-AGR-MB-03", "officer": "HC U. S. Yadav", "contact": "+91 94544 02704", "status": "AVAILABLE", "distance_m": 290}
        ],
        "active_incidents": [],
        "restricted_zones": [
            {"name": "Yamuna Riverbank Silt Hazard", "zone_type": "RESTRICTED", "risk_level": "MEDIUM", "reason": "Slippery riverbanks; stay on garden pathways."}
        ],
        "nearby_hospitals": [
            {"name": "District District Hospital Agra", "distance_km": 3.9, "phone": "+91 562 226 2222"}
        ],
        "safety_tips": "Premier spot for crowd-free sunset photography of the Taj Mahal across the Yamuna."
    },

    # ==========================================================================
    # GOA LANDMARKS
    # ==========================================================================
    {
        "id": "GOA_BAGA",
        "name": "Baga Beach Main Promenade",
        "city_code": "GOA",
        "city_name": "Goa",
        "category": "BEACH",
        "category_display": "🏖️ Popular Beach Hub",
        "latitude": 15.5528,
        "longitude": 73.7517,
        "address": "Baga Beach Road, North Goa",
        "safety_score": 94,
        "safety_level": "VERY SAFE",
        "lighting": "High Street Illumination (Well-Lit)",
        "crowd_level": "High Tourist Flow",
        "police_coverage": "Calangute-Baga Tourist Police & Lifeguard Watchtower Alpha",
        "emergency_phone": "108 / +91 832 227 7211",
        "pcr_vans": [
            {"callsign": "Patrol Unit Calangute 01", "unit_code": "PCR-CAL-01", "officer": "SI R. Naik", "contact": "+91 94220 11001", "status": "AVAILABLE", "distance_m": 210}
        ],
        "active_incidents": [],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "Candolim 24x7 EMS Trauma Care", "distance_km": 4.1, "phone": "+91 832 248 9900"}
        ],
        "safety_tips": "Lifeguard towers active from 07:00 to 18:30. Observe water flags."
    },
    {
        "id": "GOA_CALANGUTE",
        "name": "Calangute Beach Central Plaza",
        "city_code": "GOA",
        "city_name": "Goa",
        "category": "BEACH",
        "category_display": "🏖️ Popular Beach Hub",
        "latitude": 15.5439,
        "longitude": 73.7554,
        "address": "Calangute Market Circle, North Goa",
        "safety_score": 93,
        "safety_level": "VERY SAFE",
        "lighting": "Well-Lit Arterial Walkways",
        "crowd_level": "High Shopping & Dining Footfall",
        "police_coverage": "Calangute Tourist Police Station (24x7 Station)",
        "emergency_phone": "+91 832 227 7211",
        "pcr_vans": [
            {"callsign": "Calangute Police Post Unit", "unit_code": "PCR-CAL-02", "officer": "HC S. Gaonkar", "contact": "+91 94220 11002", "status": "AVAILABLE", "distance_m": 120}
        ],
        "active_incidents": [],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "Bosio Hospital Candolim Road", "distance_km": 1.2, "phone": "+91 832 227 6013"}
        ],
        "safety_tips": "Main shopping street is well-lit and monitored by tourist police checkposts."
    },
    {
        "id": "GOA_CALANGUTE_POLICE",
        "name": "Calangute Tourist Police Station",
        "city_code": "GOA",
        "city_name": "Goa",
        "category": "POLICE",
        "category_display": "👮 24x7 Tourist Police Base",
        "latitude": 15.5410,
        "longitude": 73.7570,
        "address": "Calangute Beach Road, North Goa",
        "safety_score": 98,
        "safety_level": "MAXIMUM SECURITY",
        "lighting": "24x7 Emergency Floodlighting",
        "crowd_level": "Active Police Station Hub",
        "police_coverage": "24x7 Duty Desk & Mobile Patrol Interceptors",
        "emergency_phone": "+91 832 227 7211",
        "pcr_vans": [
            {"callsign": "Calangute Police Post Unit", "unit_code": "PCR-CAL-02", "officer": "HC S. Gaonkar", "contact": "+91 94220 11002", "status": "AVAILABLE", "distance_m": 10}
        ],
        "active_incidents": [],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "Candolim 24x7 EMS Trauma Care", "distance_km": 3.2, "phone": "+91 832 248 9900"}
        ],
        "safety_tips": "Primary tourist emergency reporting center for North Goa coastal belt."
    },
    {
        "id": "GOA_PANAJI_POLICE",
        "name": "Panaji Police Station",
        "city_code": "GOA",
        "city_name": "Goa",
        "category": "POLICE",
        "category_display": "👮 Central Police HQ & Helpdesk",
        "latitude": 15.4980,
        "longitude": 73.8260,
        "address": "Near Church Square, Panaji, Goa",
        "safety_score": 99,
        "safety_level": "MAXIMUM SECURITY",
        "lighting": "Continuous High-Mast Illumination",
        "crowd_level": "Security Monitored Sector",
        "police_coverage": "24x7 Capital Police Headquarters",
        "emergency_phone": "+91 832 242 0808",
        "pcr_vans": [
            {"callsign": "Patrol Alpha PCR-01", "unit_code": "PCR-PANJIM-01", "officer": "Head Constable S. Naik", "contact": "+91 94220 11001", "status": "AVAILABLE", "distance_m": 15}
        ],
        "active_incidents": [],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "Goa Medical College (GMC Hospital)", "distance_km": 4.5, "phone": "+91 832 245 8700"}
        ],
        "safety_tips": "24x7 Tourist Police assistance desk in central Panaji."
    },
    {
        "id": "GOA_FORT_AGUADA",
        "name": "Fort Aguada & Historic Lighthouse",
        "city_code": "GOA",
        "city_name": "Goa",
        "category": "HERITAGE",
        "category_display": "🏰 Coastal Fort & Viewpoint",
        "latitude": 15.4920,
        "longitude": 73.7730,
        "address": "Sinquerim, Candolim, Goa",
        "safety_score": 91,
        "safety_level": "VERY SAFE",
        "lighting": "Architectural Night Illumination",
        "crowd_level": "Moderate Coastal Visitors",
        "police_coverage": "Candolim Police Outpost & Aguada Security Guard",
        "emergency_phone": "+91 832 248 9900",
        "pcr_vans": [
            {"callsign": "Sinquerim Coastal Patrol", "unit_code": "PCR-SINQ-01", "officer": "SI P. D'Souza", "contact": "+91 94220 11003", "status": "AVAILABLE", "distance_m": 250}
        ],
        "active_incidents": [],
        "restricted_zones": [
            {"name": "Aguada Cliffhead Drop Perimeter", "zone_type": "HIGH_RISK", "risk_level": "HIGH", "reason": "Steep sea cliff; do not climb over seawall."}
        ],
        "nearby_hospitals": [
            {"name": "Candolim EMS Medical Center", "distance_km": 2.8, "phone": "+91 832 248 9900"}
        ],
        "safety_tips": "Follow signposted heritage pathways; parking available at the top fort circle."
    },
    {
        "id": "GOA_PANAJI_CHURCH",
        "name": "Panaji Church (Our Lady of Immaculate Conception)",
        "city_code": "GOA",
        "city_name": "Goa",
        "category": "HERITAGE",
        "category_display": "⛪ Historic Church & Capital Plaza",
        "latitude": 15.4989,
        "longitude": 73.8278,
        "address": "Church Square, Panaji, Goa 403001",
        "safety_score": 96,
        "safety_level": "VERY SAFE",
        "lighting": "High Urban Heritage Lighting",
        "crowd_level": "Moderate Central Plaza Flow",
        "police_coverage": "Panaji Police HQ (50m from Church Square)",
        "emergency_phone": "+91 832 242 0808",
        "pcr_vans": [
            {"callsign": "Patrol Alpha PCR-01", "unit_code": "PCR-PANJIM-01", "officer": "Head Constable S. Naik", "contact": "+91 94220 11001", "status": "AVAILABLE", "distance_m": 90}
        ],
        "active_incidents": [],
        "restricted_zones": [],
        "nearby_hospitals": [
            {"name": "Goa Medical College (GMC Hospital)", "distance_km": 4.5, "phone": "+91 832 245 8700"}
        ],
        "safety_tips": "Extremely safe pedestrian zone. Centrally connected to Mandovi riverfront promenade."
    },
    {
        "id": "GOA_VAGATOR",
        "name": "Vagator Hilltop & Small Vagator Beach",
        "city_code": "GOA",
        "city_name": "Goa",
        "category": "BEACH",
        "category_display": "🏖️ Scenic Coastal Zone",
        "latitude": 15.6030,
        "longitude": 73.7330,
        "address": "Vagator Cliff Road, North Goa",
        "safety_score": 85,
        "safety_level": "SAFE",
        "lighting": "Moderate Illumination",
        "crowd_level": "Moderate Sunset Crowd",
        "police_coverage": "Anjuna Police Station Patrol Unit",
        "emergency_phone": "+91 832 227 3233",
        "pcr_vans": [
            {"callsign": "Anjuna Sector Patrol", "unit_code": "PCR-ANJ-01", "officer": "HC M. Fernandes", "contact": "+91 94220 11005", "status": "AVAILABLE", "distance_m": 410}
        ],
        "active_incidents": [],
        "restricted_zones": [
            {"name": "Vagator Cliffhead Restricted Perimeter", "zone_type": "RESTRICTED", "risk_level": "CRITICAL", "reason": "Steep unbarricaded cliff drop with loose gravel."}
        ],
        "nearby_hospitals": [
            {"name": "St. Anthony's Hospital Anjuna", "distance_km": 2.8, "phone": "+91 832 227 3254"}
        ],
        "safety_tips": "Do not venture near the cliff edge in low light. Stick to designated stairs."
    }
]


# ==============================================================================
# Helper Lookup & Query Functions
# ==============================================================================

def get_cities_catalog() -> List[Dict[str, Any]]:
    """Returns metadata for all supported cities."""
    return list(CITIES_METADATA.values())


def get_all_places_catalog(city: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns a unified list of places from both the static multi-city catalog
    and active database records (SafetyPOI, GeoZones).
    """
    places = list(LANDMARKS_CATALOG)

    # Filter by city if requested
    if city and city.strip() and city.upper() != "ALL":
        places = [p for p in places if p['city_code'].upper() == city.strip().upper()]

    # Supplement with database SafetyPOIs
    try:
        db_pois = SafetyPOI.objects.all()
        for p in db_pois:
            if not any(x['name'].lower() == p.name.lower() for x in places):
                icon = "🏥" if p.poi_type == "HOSPITAL" else "👮" if "POLICE" in p.poi_type else "🛡️"
                places.append({
                    "id": f"DB_POI_{p.id}",
                    "name": p.name,
                    "city_code": "GOA",
                    "city_name": "Goa",
                    "category": p.poi_type,
                    "category_display": f"{icon} {p.get_poi_type_display()}",
                    "latitude": p.latitude,
                    "longitude": p.longitude,
                    "address": p.address or "Goa Regional Sector",
                    "safety_score": 92,
                    "safety_level": "SAFE",
                    "lighting": "Well-Lit Arterial Corridor",
                    "crowd_level": "Monitored",
                    "police_coverage": "24x7 Safety Coverage",
                    "emergency_phone": p.contact_number or "112",
                    "pcr_vans": [],
                    "active_incidents": [],
                    "restricted_zones": [],
                    "nearby_hospitals": [],
                    "safety_tips": "Verified official safety landmark."
                })
    except Exception:
        pass

    return places


def search_places(query: str = "", city: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Performs case-insensitive search across place names, city names, categories, and addresses.
    """
    all_places = get_all_places_catalog(city=city)
    if not query or not query.strip():
        return all_places

    q = query.strip().lower()
    matches = []

    for p in all_places:
        name = p['name'].lower()
        city_name = p['city_name'].lower()
        city_code = p['city_code'].lower()
        address = p.get('address', '').lower()
        cat = p.get('category', '').lower()
        cat_disp = p.get('category_display', '').lower()

        if q in name or q in city_name or q in city_code or q in address or q in cat or q in cat_disp:
            score = 150 if name.startswith(q) else 120 if q == city_name or q == city_code else 100 if q in name else 70
            matches.append((score, p))

    matches.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in matches]


def get_place_by_id_or_name(identifier: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves full safety scorecard for a place by ID, exact name, or close substring.
    """
    if not identifier:
        return None

    ident = str(identifier).strip().lower()
    all_places = get_all_places_catalog()

    # 1. Exact ID match
    for p in all_places:
        if p.get('id', '').lower() == ident:
            return p

    # 2. Exact Name match
    for p in all_places:
        if p['name'].lower() == ident:
            return p

    # 3. Substring match
    matches = search_places(ident)
    if matches:
        return matches[0]

    return None


def resolve_place_to_coords(place_input: str):
    """
    Resolves place name, landmark, or coordinate string into (latitude, longitude, formatted_name).
    """
    if not place_input:
        return None

    place_str = str(place_input).strip()

    # Check if coordinate string "18.9220, 72.8347"
    if ',' in place_str:
        parts = place_str.split(',')
        try:
            lat = float(parts[0].strip())
            lng = float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                reverse_name = reverse_geocode_landmark(lat, lng)
                return lat, lng, reverse_name
        except ValueError:
            pass

    # Check place catalog
    found = get_place_by_id_or_name(place_str)
    if found:
        return found['latitude'], found['longitude'], f"{found['name']} ({found['city_name']})"

    return None


def reverse_geocode_landmark(latitude: float, longitude: float) -> str:
    """
    Finds the closest known landmark or sector name for a given coordinate pair.
    """
    all_places = get_all_places_catalog()
    closest = None
    min_dist = float('inf')

    for p in all_places:
        dist = haversine_distance(latitude, longitude, p['latitude'], p['longitude'])
        if dist < min_dist:
            min_dist = dist
            closest = p

    if closest and min_dist <= 0.8:
        return f"{closest['name']} (~{int(min_dist * 1000)}m, {closest['city_name']})"
    elif closest and min_dist <= 5.0:
        return f"Near {closest['name']}, {closest['city_name']}"
    else:
        return f"Location ({latitude:.4f}°, {longitude:.4f}°)"
