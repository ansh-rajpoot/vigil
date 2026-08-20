# VIGIL — Smart Tourist Safety Monitoring & Incident Response System

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.1-green.svg)](https://www.djangoproject.com/)
[![Django Channels](https://img.shields.io/badge/Channels-4.3-blueviolet.svg)](https://channels.readthedocs.io/)
[![Django REST Framework](https://img.shields.io/badge/DRF-3.18-red.svg)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Primary%20DB-336791.svg)](https://www.postgresql.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9.4-brightgreen.svg)](https://leafletjs.com/)

> **Smart India Hackathon (SIH 2026) Project**  
> *Smart Tourist Safety Monitoring & Incident Response System using AI, GIS, Geo-Fencing and Real-Time Emergency Response.*

---

## 📖 Executive Summary

**VIGIL** is an enterprise-grade, real-time public safety governance platform engineered to protect tourists and empower law enforcement authorities across high-density travel corridors.

The platform provides two synchronized portals:
1. **Tourist Companion Web App / Mobile PWA**: Digital Tourist ID with rotating dynamic TOTP QR code, multi-factor AI risk assessment, GIS safe route navigator, and intelligent panic SOS with false-alarm cancellation.
2. **Authority Command & Control (C2) Operations Center**: Tactical GIS operations room with layer controls, live SOS telemetry streams, automated geofence breach triage, field responder dispatch, CCTV computer vision crowd analytics, and geo-targeted emergency broadcasts.

---

## 🏛️ System Architecture & Modular Django Design

The project is architected across 11 decoupled Django apps:

```
vigil/
├── .env.example                # Environment variables template with PostgreSQL configuration
├── .env                        # Local active environment variables (git-ignored)
├── requirements.txt            # Python dependencies (psycopg2-binary, Django, Channels, etc.)
├── manage.py                   # Django management script
├── populate_demo_data.py       # Realistic Goa tourist & authority demo seeder
├── verify_system_integration.py# 14-point E2E integration test suite
├── vigil_core/
│   ├── asgi.py                 # ASGI entrypoint (HTTP + Channels WebSocket routing)
│   ├── wsgi.py                 # WSGI entrypoint
│   ├── settings.py             # PostgreSQL primary configuration, DRF, Channels, CORS
│   ├── routing.py              # WebSocket URL router
│   └── urls.py                 # Master URL configuration
├── apps/
│   ├── accounts/               # Custom User model, RBAC (Tourist, Operator, Responder), Emergency Contacts
│   ├── tourists/               # TouristProfile, travel telemetry, safe check-in
│   ├── digital_id/             # DigitalTouristID, rotating TOTP QR codes, verification logs
│   ├── geofencing/             # GeoZone (Polygons), containment checker, breach logs
│   ├── incidents/              # Safety reports, severity classification, full audit timeline
│   ├── emergency/              # SOSAlert, ResponderUnit, SOSDispatch, live WebSocket beacons
│   ├── risk/                   # Multi-factor AI Tourist Risk Scoring engine (0-100), Blackspots
│   ├── maps/                   # Leaflet GIS, Safety POIs, Safe Route recommendation with blackspot evasion
│   ├── alerts/                 # EmergencyBroadcast (geo-targeted warnings, siren advisories)
│   ├── dashboard/              # Authority C2 Operations Center master console & telemetry feeds
│   ├── ai_services/            # OpenCV/Computer Vision crowd counting, density & anomaly detection
│   └── common/                 # Spatial math, ray-casting point-in-polygon, HMAC TOTP crypto
├── static/
│   ├── css/
│   │   ├── design_system.css   # GovTech design tokens, typography, surfaces, badges
│   │   ├── tourist.css         # Tourist Companion portal styling
│   │   ├── c2_dashboard.css    # Authority tactical dark operations center styling
│   │   └── leaflet_custom.css  # Custom GIS map pins, radar pulses & popups
│   └── js/
│       ├── tourist_app.js      # Digital ID 3D flip, TOTP refresh timer, SOS countdown
│       ├── c2_operations.js    # C2 live Leaflet map, WebSocket feed, triage drawer
│       ├── safe_routing.js     # Leaflet safe route waypoint planner & metrics
│       └── qr_scanner.js       # Police / Hotel checkpoint QR camera scanner
└── templates/
    ├── base.html               # Base HTML5 shell for Tourist Companion
    ├── base_c2.html            # Full-height tactical C2 shell
    ├── design_system_preview.html # Live design system showcase
    ├── components/             # Reusable masthead, navbar, footer, badges, cards
    ├── tourist/                # Tourist portal views (home, digital ID, safe routes, SOS active)
    ├── authority/              # Authority C2 views (command center, incidents, geofences, CCTV AI, broadcast)
    ├── public/                 # Checkpoint QR verification portal
    └── auth/                   # Login & registration views
```

---

## 🗄️ Database Setup: PostgreSQL Installation & Configuration

PostgreSQL is the **primary and default database** for the VIGIL system.

### Step 1: Install PostgreSQL

#### On macOS (Homebrew):
```bash
brew install postgresql@16
brew services start postgresql@16
```

#### On Linux (Ubuntu / Debian):
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib libpq-dev
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Step 2: Create PostgreSQL Database & Dedicated User
Open the PostgreSQL prompt:
```bash
# On macOS / Linux:
psql -U postgres
# Or on macOS default:
psql postgres
```

Run the SQL setup commands:
```sql
CREATE DATABASE vigil_db;
CREATE USER vigil_user WITH PASSWORD 'vigil_password_2026';
GRANT ALL PRIVILEGES ON DATABASE vigil_db TO vigil_user;
ALTER DATABASE vigil_db OWNER TO vigil_user;
ALTER USER vigil_user CREATEDB;

\c vigil_db
GRANT ALL ON SCHEMA public TO vigil_user;
ALTER SCHEMA public OWNER TO vigil_user;
```

### Step 3: Configure Environment Variables (`.env`)
Create your `.env` file from the provided template:
```bash
cp .env.example .env
```
Ensure the following PostgreSQL environment variables are configured:
```ini
DB_NAME=vigil_db
DB_USER=vigil_user
DB_PASSWORD=vigil_password_2026
DB_HOST=localhost
DB_PORT=5432

# Or optional complete connection URL:
DATABASE_URL=postgresql://vigil_user:vigil_password_2026@localhost:5432/vigil_db
```

### Step 4: Run Migrations against PostgreSQL
```bash
source venv/bin/activate
python manage.py migrate
```

### Step 5: Seed Demo Scenario Data into PostgreSQL
```bash
python populate_demo_data.py
```

### Step 6: Start the Django / ASGI Server
```bash
python manage.py runserver 127.0.0.1:8000
```
Visit: `http://127.0.0.1:8000/`

---

## 🧪 Verification & Testing Suite

### Run Automated Unit Tests:
```bash
python manage.py test common digital_id risk
```
* **Status**: `6/6 passed (100% OK)`

### Run Full End-to-End Integration Suite:
```bash
python verify_system_integration.py
```
* **Status**: `14/14 critical workflows verified against PostgreSQL database`

---

## 🔑 Demonstration Credentials (SIH Presentation)

| Role | Username | Password | Access Portals |
| :--- | :--- | :--- | :--- |
| **Tourist** | `tourist_ananya` | `pass1234` | Tourist Home, Digital ID Card, Safe Routes, SOS Trigger |
| **Tourist 2** | `tourist_rahul` | `pass1234` | Secondary tourist in caution sector |
| **C2 Operator** | `officer_sharma` | `pass1234` | Authority Command & Control Room, Dispatch, Geofences, CCTV AI |

### Key Showcase URLs:
* **Tourist Safety Companion**: `http://127.0.0.1:8000/tourist/`
* **Digital Tourist ID (3D Flip & Rotating QR)**: `http://127.0.0.1:8000/digital-id/card/`
* **Safe Route GIS Navigator**: `http://127.0.0.1:8000/maps/safe-routes/`
* **Checkpoint QR Scanner**: `http://127.0.0.1:8000/digital-id/verify/`
* **Authority C2 Operations Center**: `http://127.0.0.1:8000/dashboard/c2/`
* **Incident Triage & Assignment**: `http://127.0.0.1:8000/incidents/c2/`
* **Geofence Spatial Zone Manager**: `http://127.0.0.1:8000/geofencing/manager/`
* **AI CCTV Vision Intelligence**: `http://127.0.0.1:8000/ai-services/c2/`
* **Emergency Broadcast Dispatcher**: `http://127.0.0.1:8000/alerts/c2/`
* **Design System Showcase**: `http://127.0.0.1:8000/design-system/`
