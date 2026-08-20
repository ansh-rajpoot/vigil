#!/usr/bin/env bash
# ==============================================================================
# VIGIL — Render Production Build Script
# Executes dependency installation, static files collection, and database migrations.
# ==============================================================================

# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "======================================================="
echo "🚀 [1/3] Installing Python Dependencies..."
echo "======================================================="
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "======================================================="
echo "📦 [2/3] Collecting Static Assets (WhiteNoise)..."
echo "======================================================="
python manage.py collectstatic --no-input

echo "======================================================="
echo "🗄️ [3/3] Applying PostgreSQL Database Migrations..."
echo "======================================================="
python manage.py migrate --no-input

echo "======================================================="
echo "✅ Build Completed Successfully! Ready for ASGI Start."
echo "======================================================="
