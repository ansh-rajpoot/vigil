# 🚀 Deploying VIGIL to Render (Production Guide)

This guide walks you through deploying **VIGIL** (Smart Tourist Safety & Incident Response System) to **[Render.com](https://render.com)** using **PostgreSQL**, **Django ASGI / Channels**, and **WebSockets**.

---

## 🏗️ Architecture Overview on Render

```
                             [ User Browser / Mobile Device ]
                                            │
                                  HTTPS / WSS Connection
                                            │
                                            ▼
                             [ Render Cloud Load Balancer ]
                                            │
                                  Port $PORT (HTTP & WS)
                                            │
                                            ▼
                      [ Daphne ASGI Server (vigil_core.asgi) ]
                                            │
                  ┌─────────────────────────┴─────────────────────────┐
                  ▼                                                   ▼
      [ WhiteNoise Static Assets ]                             [ Django Channels ASGI ]
      (CSS, JS, Leaflet, Fonts)                                (C2 Telemetry & SOS WebSockets)
                  │                                                   │
                  ▼                                                   ▼
    [ Managed PostgreSQL Database ]                           [ Optional Redis Cache / Layer ]
```

---

## ⚡ Method 1: Automated 1-Click Deployment via Blueprint (`render.yaml`)

Render supports **Blueprints (Infrastructure as Code)** which automatically creates both the **Web Service** and the **Managed PostgreSQL Database** in one step.

1. **Push your code to GitHub / GitLab**.
2. Log in to your **[Render Dashboard](https://dashboard.render.com/)**.
3. Click **"New +"** and select **"Blueprint"**.
4. Connect your repository containing `render.yaml`.
5. Render will automatically detect:
   - **PostgreSQL Database**: `vigil-postgres-db`
   - **Web Service**: `vigil-public-safety`
   - **Build Command**: `./build.sh`
   - **Start Command**: `daphne -b 0.0.0.0 -p $PORT vigil_core.asgi:application`
6. Click **"Apply"** to deploy.

---

## 🛠️ Method 2: Manual Step-by-Step Setup on Render

If you prefer to configure services manually in the Render dashboard:

### Step 1: Create a PostgreSQL Database
1. In the Render dashboard, click **"New +"** &rarr; **"PostgreSQL"**.
2. Configure:
   - **Name**: `vigil-postgres-db`
   - **Database**: `vigil_db`
   - **User**: `vigil_user`
   - **Region**: Select closest to your audience (e.g. *Oregon* or *Frankfurt*).
   - **Plan**: `Free` or higher.
3. Click **"Create Database"**.
4. Once created, copy the **Internal Database URL** (e.g. `postgresql://vigil_user:...@dpg-...:5432/vigil_db`).

---

### Step 2: Create the Web Service
1. In the Render dashboard, click **"New +"** &rarr; **"Web Service"**.
2. Connect your Git repository.
3. Fill in the service configuration:
   - **Name**: `vigil-public-safety`
   - **Region**: Same region as your database.
   - **Runtime**: `Python`
   - **Branch**: `main` (or your default branch)
   - **Build Command**:
     ```bash
     ./build.sh
     ```
   - **Start Command** *(Crucial for WebSockets & Channels)*:
     ```bash
     daphne -b 0.0.0.0 -p $PORT vigil_core.asgi:application
     ```
   - **Plan**: `Free` (or higher)

---

### Step 3: Configure Environment Variables

Under the **"Environment"** tab of your Web Service, add the following variables:

| Key | Example Value | Description |
| :--- | :--- | :--- |
| `PYTHON_VERSION` | `3.12.8` | Enforces Python 3.12 runtime |
| `SECRET_KEY` | *(Click "Generate" or enter random string)* | Production Django secret key |
| `DEBUG` | `False` | Disables debug mode in production |
| `DATABASE_URL` | `postgresql://vigil_user:pass@dpg-...:5432/vigil_db` | Connection string from Step 1 |
| `ALLOWED_HOSTS` | `.onrender.com,localhost,127.0.0.1` | Hostnames allowed by Django |
| `CSRF_TRUSTED_ORIGINS` | `https://*.onrender.com` | Prevents 403 CSRF verification errors |
| `CHANNEL_LAYER_BACKEND`| `inmemory` | In-memory or `redis` if Redis instance added |
| `SECURE_SSL_REDIRECT` | `True` | Enforces HTTPS redirection |
| `SESSION_COOKIE_SECURE`| `True` | Transmits session cookies only over HTTPS |
| `CSRF_COOKIE_SECURE` | `True` | Transmits CSRF cookies only over HTTPS |

---

### Step 4: Seed Demo Data & Create Admin Account

Once the first deploy finishes successfully, open the Render Web Service **"Shell"** tab in your browser and run:

```bash
# 1. Seed demo accounts, GIS zones, blackspots, and responder units
python populate_demo_data.py

# 2. (Optional) Create a custom superuser if needed
python manage.py createsuperuser
```

---

## 🛡️ Pre-Configured Demo Accounts for SIH Evaluation

| Role | Username | Password | Dashboard URL |
| :--- | :--- | :--- | :--- |
| **Authority C2 Officer** | `officer_sharma` | `pass1234` | `/dashboard/c2/` |
| **Monitored Tourist** | `tourist_ananya` | `pass1234` | `/tourist/` |
| **Tourism Administrator**| `admin_rajesh` | `pass1234` | `/auth/admin-portal/` |
| **Field Police Checkpoint**| `officer_patil` | `pass1234` | `/digital-id/verify-portal/` |

---

## 🔍 Verification & Troubleshooting Checklist

### 1. WebSockets Disconnecting or Failing on Render?
* Make sure your Start Command is using **Daphne ASGI**:
  `daphne -b 0.0.0.0 -p $PORT vigil_core.asgi:application`
* Do **NOT** use `gunicorn vigil_core.wsgi:application` as standard WSGI does not support WebSocket streaming.

### 2. Static CSS / Leaflet Icons Not Loading?
* VIGIL uses **WhiteNoise** with `CompressedStaticFilesStorage`.
* `./build.sh` automatically runs `python manage.py collectstatic --no-input`.
* Check that `staticfiles/` is built during deployment.

### 3. CSRF Verification Failed (403 Forbidden)?
* Ensure `CSRF_TRUSTED_ORIGINS` contains `https://*.onrender.com` or your exact URL `https://<service-name>.onrender.com`.

### 4. Database Connection Refused / SSL Mode?
* `dj-database-url` in `vigil_core/settings.py` is configured with `ssl_require=True` automatically for Render PostgreSQL endpoints.
