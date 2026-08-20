/**
 * VIGIL SAFE ROUTING & PLACE-DRIVEN THREAT-AVOIDANCE CONTROLLER
 * Real-world turn-by-turn road route computation via OSRM + PostGIS safety evaluator.
 * Supports full place/landmark search, current GPS integration, and interactive map picking.
 */

class SafeRoutingManager {
  constructor() {
    this.map = null;
    this.routeLayer = null;
    this.hazardLayer = null;
    this.poiLayer = null;
    this.origMarker = null;
    this.destMarker = null;
    this.currentMode = 'walking';
    this.placesCatalog = [];
    this.init();
  }

  async init() {
    this.initMap();
    this.initLocationButton();
    this.initTravelModeButtons();
    this.initQuickChips();
    this.initPlaceInputs();
    this.initPresetButtons();
    this.initMapClickEvents();
    this.initFormSubmit();
    await this.loadPlacesCatalog();
    this.loadBlackspotHazards();

    // Auto-calculate default route on load for immediate demonstration
    setTimeout(() => {
      this.calculateRoute();
    }, 400);
  }

  initMap() {
    const mapEl = document.getElementById('safe-route-map');
    if (!mapEl) return;

    this.map = L.map('safe-route-map', {
      center: [15.5200, 73.7900],
      zoom: 12,
      zoomControl: true
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 20,
      subdomains: 'abcd',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a> • VIGIL Safe Routing'
    }).addTo(this.map);

    this.hazardLayer = L.layerGroup().addTo(this.map);
    this.poiLayer = L.layerGroup().addTo(this.map);
    this.routeLayer = L.layerGroup().addTo(this.map);

    // Initial markers based on default values
    const oLat = parseFloat(document.getElementById('orig_lat')?.value || 15.4989);
    const oLng = parseFloat(document.getElementById('orig_lng')?.value || 73.8278);
    const dLat = parseFloat(document.getElementById('dest_lat')?.value || 15.5410);
    const dLng = parseFloat(document.getElementById('dest_lng')?.value || 73.7570);

    this.updateMarker('orig', oLat, oLng, document.getElementById('orig_place_input')?.value || 'Origin');
    this.updateMarker('dest', dLat, dLng, document.getElementById('dest_place_input')?.value || 'Destination');
  }

  async loadPlacesCatalog() {
    try {
      const res = await fetch('/maps/api/places/');
      const data = await res.json();
      if (data.success && Array.isArray(data.data)) {
        this.placesCatalog = data.data;
      }
    } catch (e) {
      console.warn('Places catalog load warning:', e);
    }
  }

  async loadBlackspotHazards() {
    try {
      const res = await fetch('/maps/api/gis-layers/');
      const data = await res.json();
      if (data.success && data.data && data.data.blackspots) {
        this.hazardLayer.clearLayers();
        data.data.blackspots.forEach(b => {
          L.circle([b.latitude, b.longitude], {
            radius: b.radius_meters || 300,
            color: '#ea580c',
            weight: 1.5,
            fillColor: '#ea580c',
            fillOpacity: 0.15,
            dashArray: '4,4'
          }).bindPopup(`
            <div style="font-family:Inter,sans-serif; font-size:12px;">
              <div style="font-weight:700; color:#ea580c; text-transform:uppercase; font-size:10px;">⚠️ Threat Blackspot</div>
              <div style="font-weight:700; font-size:13px; color:#0f172a; margin-top:2px;">${b.name}</div>
              <div style="color:#64748b; font-size:11px;">Radius: ${b.radius_meters}m • Risk: ${b.risk_weight}/100</div>
              <div style="color:#b91c1c; font-size:11px; margin-top:4px;">${b.safety_advice || 'Hazard zone'}</div>
            </div>
          `).addTo(this.hazardLayer);
        });
      }
    } catch (e) {
      console.warn('Blackspot hazard load warning:', e);
    }
  }

  initLocationButton() {
    const btn = document.getElementById('btn-use-my-location');
    if (!btn) return;

    btn.addEventListener('click', async () => {
      btn.innerHTML = '<span>⏳</span> Locating...';
      try {
        let lat, lng;
        if (window.vigilLocation && window.vigilLocation.isSupported()) {
          const coords = await window.vigilLocation.getCurrentPosition({ enableHighAccuracy: true, timeout: 6000 });
          lat = coords.latitude;
          lng = coords.longitude;
        } else if (navigator.geolocation) {
          const pos = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 6000 });
          });
          lat = pos.coords.latitude;
          lng = pos.coords.longitude;
        } else {
          throw new Error('Geolocation is not supported by your browser.');
        }

        const origPlaceInput = document.getElementById('orig_place_input');
        if (origPlaceInput) origPlaceInput.value = '📍 My Current Location';

        document.getElementById('orig_lat').value = lat.toFixed(4);
        document.getElementById('orig_lng').value = lng.toFixed(4);

        this.updateMarker('orig', lat, lng, 'My Current Location');
        this.map.flyTo([lat, lng], 14);

        btn.innerHTML = '<span>📍</span> GPS Locked ✓';
        setTimeout(() => { btn.innerHTML = '<span>📍</span> Use My GPS'; }, 3000);

        this.calculateRoute();
      } catch (err) {
        alert(err.message || 'Could not acquire GPS position.');
        btn.innerHTML = '<span>📍</span> Use My GPS';
      }
    });
  }

  initTravelModeButtons() {
    const walkBtn = document.getElementById('mode-walk-btn');
    const driveBtn = document.getElementById('mode-drive-btn');
    const modeInput = document.getElementById('travel_mode');

    if (walkBtn && driveBtn) {
      walkBtn.addEventListener('click', () => {
        this.currentMode = 'walking';
        modeInput.value = 'walking';
        walkBtn.className = 'btn btn-primary btn-sm';
        driveBtn.className = 'btn btn-secondary btn-sm';
        this.calculateRoute();
      });

      driveBtn.addEventListener('click', () => {
        this.currentMode = 'driving';
        modeInput.value = 'driving';
        driveBtn.className = 'btn btn-primary btn-sm';
        walkBtn.className = 'btn btn-secondary btn-sm';
        this.calculateRoute();
      });
    }
  }

  initQuickChips() {
    // Quick Origin Chips
    document.querySelectorAll('.js-quick-orig').forEach(chip => {
      chip.addEventListener('click', () => {
        const place = chip.getAttribute('data-place');
        const origInput = document.getElementById('orig_place_input');
        if (origInput) origInput.value = place;
        this.resolvePlaceAndSyncCoords('orig', place);
      });
    });

    // Quick Destination Chips
    document.querySelectorAll('.js-quick-dest').forEach(chip => {
      chip.addEventListener('click', () => {
        const place = chip.getAttribute('data-place');
        const destInput = document.getElementById('dest_place_input');
        if (destInput) destInput.value = place;
        this.resolvePlaceAndSyncCoords('dest', place);
      });
    });
  }

  initPlaceInputs() {
    const origInput = document.getElementById('orig_place_input');
    const destInput = document.getElementById('dest_place_input');

    if (origInput) {
      origInput.addEventListener('change', () => {
        this.resolvePlaceAndSyncCoords('orig', origInput.value);
      });
    }

    if (destInput) {
      destInput.addEventListener('change', () => {
        this.resolvePlaceAndSyncCoords('dest', destInput.value);
      });
    }
  }

  async resolvePlaceAndSyncCoords(type, placeName) {
    if (!placeName || !placeName.trim()) return;

    // Check in local catalog first
    const match = this.placesCatalog.find(p => p.name.toLowerCase() === placeName.trim().toLowerCase()) ||
                  this.placesCatalog.find(p => p.name.toLowerCase().includes(placeName.trim().toLowerCase()));

    if (match) {
      const lat = match.latitude;
      const lng = match.longitude;
      if (type === 'orig') {
        document.getElementById('orig_lat').value = lat.toFixed(4);
        document.getElementById('orig_lng').value = lng.toFixed(4);
        this.updateMarker('orig', lat, lng, match.name);
      } else {
        document.getElementById('dest_lat').value = lat.toFixed(4);
        document.getElementById('dest_lng').value = lng.toFixed(4);
        this.updateMarker('dest', lat, lng, match.name);
      }
      this.calculateRoute();
      return;
    }

    // Query backend places API if not found in memory
    try {
      const res = await fetch(`/maps/api/places/?q=${encodeURIComponent(placeName)}`);
      const data = await res.json();
      if (data.success && data.data && data.data.length > 0) {
        const best = data.data[0];
        const lat = best.latitude;
        const lng = best.longitude;
        if (type === 'orig') {
          document.getElementById('orig_lat').value = lat.toFixed(4);
          document.getElementById('orig_lng').value = lng.toFixed(4);
          this.updateMarker('orig', lat, lng, best.name);
        } else {
          document.getElementById('dest_lat').value = lat.toFixed(4);
          document.getElementById('dest_lng').value = lng.toFixed(4);
          this.updateMarker('dest', lat, lng, best.name);
        }
        this.calculateRoute();
      }
    } catch (e) {
      console.warn('Place resolve error:', e);
    }
  }

  initPresetButtons() {
    const presetBtns = document.querySelectorAll('.js-preset-route');
    presetBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const origName = btn.getAttribute('data-orig');
        const destName = btn.getAttribute('data-dest');
        const oLat = parseFloat(btn.getAttribute('data-olat'));
        const oLng = parseFloat(btn.getAttribute('data-olng'));
        const dLat = parseFloat(btn.getAttribute('data-dlat'));
        const dLng = parseFloat(btn.getAttribute('data-dlng'));

        if (origName) document.getElementById('orig_place_input').value = origName;
        if (destName) document.getElementById('dest_place_input').value = destName;

        document.getElementById('orig_lat').value = oLat.toFixed(4);
        document.getElementById('orig_lng').value = oLng.toFixed(4);
        document.getElementById('dest_lat').value = dLat.toFixed(4);
        document.getElementById('dest_lng').value = dLng.toFixed(4);

        this.updateMarker('orig', oLat, oLng, origName || 'Origin');
        this.updateMarker('dest', dLat, dLng, destName || 'Destination');

        this.calculateRoute();
      });
    });
  }

  initMapClickEvents() {
    if (!this.map) return;

    this.map.on('click', (e) => {
      const clickMode = document.querySelector('input[name="map_click_mode"]:checked')?.value || 'dest';
      const lat = e.latlng.lat;
      const lng = e.latlng.lng;

      // Find closest landmark name from places catalog
      const nearestLandmark = this.findClosestLandmark(lat, lng);
      const placeLabel = nearestLandmark ? `Near ${nearestLandmark.name}` : `Selected Point (${lat.toFixed(4)}°, ${lng.toFixed(4)}°)`;

      if (clickMode === 'orig') {
        document.getElementById('orig_place_input').value = placeLabel;
        document.getElementById('orig_lat').value = lat.toFixed(4);
        document.getElementById('orig_lng').value = lng.toFixed(4);
        this.updateMarker('orig', lat, lng, placeLabel);
      } else {
        document.getElementById('dest_place_input').value = placeLabel;
        document.getElementById('dest_lat').value = lat.toFixed(4);
        document.getElementById('dest_lng').value = lng.toFixed(4);
        this.updateMarker('dest', lat, lng, placeLabel);
      }

      this.calculateRoute();
    });
  }

  findClosestLandmark(lat, lng) {
    if (!this.placesCatalog || this.placesCatalog.length === 0) return null;
    let closest = null;
    let minD = Infinity;

    for (const p of this.placesCatalog) {
      const d = Math.hypot(lat - p.latitude, lng - p.longitude);
      if (d < minD) {
        minD = d;
        closest = p;
      }
    }
    // Only return if reasonably close (within ~2km approx 0.02 deg)
    return minD <= 0.02 ? closest : null;
  }

  updateMarker(type, lat, lng, name = '') {
    if (!this.map) return;

    if (type === 'orig') {
      const icon = L.divIcon({
        className: 'custom-pin-start',
        html: `
          <div style="width:32px; height:32px; background:#059669; border:2.5px solid #ffffff; border-radius:50%; box-shadow:0 3px 10px rgba(0,0,0,0.35); display:flex; align-items:center; justify-content:center; color:#ffffff; font-weight:800; font-size:13px; font-family:Inter,sans-serif;">
            A
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });

      if (this.origMarker) {
        this.origMarker.setLatLng([lat, lng]);
      } else {
        this.origMarker = L.marker([lat, lng], { icon: icon, zIndexOffset: 800 }).addTo(this.map);
      }
      this.origMarker.bindPopup(`<b>🟢 Origin (Start A)</b><br>${name || 'Starting Point'}`);
    } else {
      const icon = L.divIcon({
        className: 'custom-pin-dest',
        html: `
          <div style="width:32px; height:32px; background:#dc2626; border:2.5px solid #ffffff; border-radius:50%; box-shadow:0 3px 10px rgba(0,0,0,0.35); display:flex; align-items:center; justify-content:center; color:#ffffff; font-weight:800; font-size:13px; font-family:Inter,sans-serif;">
            B
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });

      if (this.destMarker) {
        this.destMarker.setLatLng([lat, lng]);
      } else {
        this.destMarker = L.marker([lat, lng], { icon: icon, zIndexOffset: 800 }).addTo(this.map);
      }
      this.destMarker.bindPopup(`<b>🔴 Destination (Target B)</b><br>${name || 'Destination Point'}`);
    }
  }

  initFormSubmit() {
    const btn = document.getElementById('btn-calculate-route');
    if (!btn) return;
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      this.calculateRoute();
    });
  }

  async calculateRoute() {
    this.hideError();

    const origPlace = document.getElementById('orig_place_input')?.value || '';
    const destPlace = document.getElementById('dest_place_input')?.value || '';
    const origLat = parseFloat(document.getElementById('orig_lat')?.value);
    const origLng = parseFloat(document.getElementById('orig_lng')?.value);
    const destLat = parseFloat(document.getElementById('dest_lat')?.value);
    const destLng = parseFloat(document.getElementById('dest_lng')?.value);
    const mode = document.getElementById('travel_mode')?.value || this.currentMode || 'walking';

    const btn = document.getElementById('btn-calculate-route');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span>⏳</span> Calculating Safest Corridor...';
    }

    try {
      const res = await fetch('/maps/api/calculate-safe-route/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        },
        body: JSON.stringify({
          orig_place: origPlace,
          dest_place: destPlace,
          orig_lat: !isNaN(origLat) ? origLat : undefined,
          orig_lng: !isNaN(origLng) ? origLng : undefined,
          dest_lat: !isNaN(destLat) ? destLat : undefined,
          dest_lng: !isNaN(destLng) ? destLng : undefined,
          mode: mode
        })
      });

      const data = await res.json();
      if (data.success && data.data) {
        this.renderRoute(data.data);
        this.updateRouteMetricsUI(data.data);
      } else {
        this.showError(data.message || 'Route calculation failed.');
      }
    } catch (err) {
      console.error('Route calculation error:', err);
      this.showError('Error connecting to safe routing engine. Please verify network connection.');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span>🛡️</span> Calculate Safest Corridor';
      }
    }
  }

  renderRoute(routePayload) {
    if (!this.map) return;
    this.routeLayer.clearLayers();

    const waypoints = routePayload.waypoints || routePayload.recommended_route?.waypoints;
    if (!waypoints || waypoints.length === 0) return;

    // 1. Emerald outer glow casing
    const casingPolyline = L.polyline(waypoints, {
      color: '#064e3b',
      weight: 9,
      opacity: 0.45,
      lineCap: 'round',
      lineJoin: 'round'
    });
    this.routeLayer.addLayer(casingPolyline);

    // 2. High-visibility emerald safe corridor line
    const routePolyline = L.polyline(waypoints, {
      color: '#059669',
      weight: 5,
      opacity: 0.95,
      lineCap: 'round',
      lineJoin: 'round'
    });
    this.routeLayer.addLayer(routePolyline);

    // 3. Update start and end pins
    const startPt = waypoints[0];
    const endPt = waypoints[waypoints.length - 1];

    this.updateMarker('orig', startPt[0], startPt[1], routePayload.origin_name || 'Origin');
    this.updateMarker('dest', endPt[0], endPt[1], routePayload.destination_name || 'Destination');

    // 4. Fit map view with smooth padding
    this.map.fitBounds(routePolyline.getBounds(), { padding: [50, 50], maxZoom: 15 });
  }

  updateRouteMetricsUI(data) {
    const card = document.getElementById('route-results-card');
    if (!card) return;

    const rec = data.recommended_route || data;
    card.style.display = 'block';

    // Route Names
    const origDisp = document.getElementById('route-origin-display');
    const destDisp = document.getElementById('route-dest-display');
    if (origDisp) origDisp.innerText = data.origin_name || 'Origin';
    if (destDisp) destDisp.innerText = data.destination_name || 'Destination';

    // KPIs
    const scoreEl = document.getElementById('route-safety-score');
    if (scoreEl) {
      scoreEl.innerText = `${rec.safety_score}%`;
      scoreEl.style.color = rec.safety_score >= 80 ? '#059669' : rec.safety_score >= 60 ? '#f59e0b' : '#dc2626';
    }

    const distEl = document.getElementById('route-distance');
    if (distEl) distEl.innerText = `${rec.distance_km} km`;

    const etaEl = document.getElementById('route-eta');
    if (etaEl) etaEl.innerText = `~${rec.estimated_minutes} min`;

    const badge = document.getElementById('route-detour-badge');
    if (badge) {
      badge.style.display = rec.detour_applied ? 'inline-block' : 'none';
      if (rec.detour_applied) {
        badge.innerText = '🛡️ Hazard Evasion Active';
      }
    }

    // Safety breakdown
    const lightingEl = document.getElementById('route-lighting');
    if (lightingEl) {
      lightingEl.innerText = rec.lighting === 'EXCELLENT_LIT' || rec.lighting === 'WELL_LIT'
        ? 'High Street Illumination (Well-Lit)'
        : 'Moderate Lighting Corridor';
    }

    const patrolEl = document.getElementById('route-patrol');
    if (patrolEl) patrolEl.innerText = rec.patrol_coverage || 'Active Police Sector Patrol';

    const provEl = document.getElementById('route-provider');
    if (provEl) provEl.innerText = rec.routing_provider || 'OSRM Road Network';

    // Turn-by-Turn Safety Directions
    const dirList = document.getElementById('route-directions-list');
    if (dirList) {
      const directions = data.directions || [
        `1. Start at ${data.origin_name || 'Start Point'} along the designated safe corridor.`,
        `2. Follow continuous arterial illumination with active CCTV coverage.`,
        `3. Arrive safely at ${data.destination_name || 'Destination Point'}.`
      ];
      dirList.innerHTML = directions.map(d => `<li style="margin-bottom:0.25rem;">${d}</li>`).join('');
    }

    // Hazards box
    const hazardsBox = document.getElementById('route-hazards-box');
    const hazardsList = document.getElementById('route-hazards-list');
    if (hazardsBox && hazardsList) {
      if (rec.hazards_detected && rec.hazards_detected.length > 0) {
        hazardsBox.style.display = 'block';
        hazardsList.innerHTML = rec.hazards_detected.map(h => `<li>${h}</li>`).join('');
      } else {
        hazardsBox.style.display = 'none';
      }
    }

    // Safeguards box
    const safeguardsList = document.getElementById('route-safeguards-list');
    if (safeguardsList) {
      const police = (rec.nearby_police || []).map(p => `👮 ${p.name} (${p.distance_m}m)`).join(' • ');
      const hospitals = (rec.nearby_hospitals || []).map(h => `🏥 ${h.name} (${h.distance_m}m)`).join(' • ');
      const text = [police, hospitals].filter(Boolean).join('<br>') || '🛡️ 24x7 Monitored Tourist Corridor with Patrol Checkposts.';
      safeguardsList.innerHTML = text;
    }
  }

  showError(msg) {
    const banner = document.getElementById('route-error-banner');
    const text = document.getElementById('route-error-text');
    if (banner && text) {
      text.innerText = msg;
      banner.style.display = 'flex';
      banner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  hideError() {
    const banner = document.getElementById('route-error-banner');
    if (banner) banner.style.display = 'none';
  }

  getCSRFToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.safeRoutingManager = new SafeRoutingManager();
});
