/**
 * VIGIL C2 COMMAND & CONTROL OPERATIONS ENGINE
 * Real-time GIS Tactical Map, WebSocket feed listener, triage manager & unit dispatch.
 */

class C2OperationsManager {
  constructor() {
    this.map = null;
    this.ws = null;
    this.layers = {
      sos: L.layerGroup(),
      responders: L.layerGroup(),
      zones: L.layerGroup(),
      blackspots: L.layerGroup(),
      cameras: L.layerGroup(),
      pois: L.layerGroup()
    };
    this.audioAlert = null;
    this.activeSosMarkers = {};
    this.responderMarkers = {};
    this.init();
  }

  init() {
    this.initTacticalMap();
    this.initLayerToggles();
    this.initWebSocket();
    this.initTriageTabs();
    this.initAudio();
    this.loadInitialTelemetry();
  }

  initAudio() {
    // Web Audio synthesizer beep for incoming SOS
    try {
      this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    } catch (e) {}
  }

  playAlertSound(freq = 880, type = 'sine') {
    if (!this.audioCtx) return;
    try {
      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, this.audioCtx.currentTime);
      gain.gain.setValueAtTime(0.15, this.audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + 0.4);
      osc.connect(gain);
      gain.connect(this.audioCtx.destination);
      osc.start();
      osc.stop(this.audioCtx.currentTime + 0.4);
    } catch (e) {}
  }

  // --- Tactical GIS Map ---
  initTacticalMap() {
    const mapEl = document.getElementById('c2-tactical-map');
    if (!mapEl) return;

    // Center on Goa / Demo coordinates
    this.map = L.map('c2-tactical-map', {
      center: [15.4989, 73.8278],
      zoom: 12,
      zoomControl: true
    });

    // Dark Tactical CartoDB Tile Layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19
    }).addTo(this.map);

    // Add layer groups to map
    Object.values(this.layers).forEach(layer => layer.addTo(this.map));
  }

  initLayerToggles() {
    const toggles = document.querySelectorAll('.js-map-layer-toggle');
    toggles.forEach(toggle => {
      toggle.addEventListener('change', (e) => {
        const layerName = e.target.getAttribute('data-layer');
        if (this.layers[layerName]) {
          if (e.target.checked) {
            this.map.addLayer(this.layers[layerName]);
          } else {
            this.map.removeLayer(this.layers[layerName]);
          }
        }
      });
    });
  }

  // --- Initial Telemetry Fetch ---
  async loadInitialTelemetry() {
    try {
      const res = await fetch('/dashboard/api/telemetry/');
      const data = await res.json();
      if (data.success && data.data) {
        this.renderTelemetryData(data.data);
      }
    } catch (e) {
      console.warn('Initial telemetry load:', e);
    }
  }

  renderTelemetryData(data) {
    // 1. Render Geofence Zones
    if (data.geozones) {
      this.layers.zones.clearLayers();
      data.geozones.forEach(zone => {
        if (zone.polygon_geojson) {
          const color = zone.zone_type === 'SAFE_HAVEN' ? '#059669' :
                        zone.zone_type === 'RESTRICTED' ? '#dc2626' :
                        zone.zone_type === 'HIGH_RISK' ? '#ea580c' : '#f59e0b';

          const polygon = L.geoJSON(zone.polygon_geojson, {
            style: {
              color: color,
              weight: 2,
              opacity: 0.8,
              fillColor: color,
              fillOpacity: 0.15
            }
          });

          polygon.bindPopup(`
            <div class="popup-title">${zone.name}</div>
            <div class="popup-meta">Type: <b>${zone.zone_type}</b></div>
            <div>${zone.safety_advisory || zone.description || ''}</div>
          `);
          this.layers.zones.addLayer(polygon);
        }
      });
    }

    // 2. Render Blackspots
    if (data.blackspots) {
      this.layers.blackspots.clearLayers();
      data.blackspots.forEach(b => {
        const circle = L.circle([b.latitude, b.longitude], {
          radius: b.radius_meters || 300,
          color: '#ea580c',
          weight: 1.5,
          fillColor: '#ea580c',
          fillOpacity: 0.2
        });

        circle.bindPopup(`
          <div class="popup-title">${b.name}</div>
          <div class="popup-meta">Category: ${b.category_display} | Risk: ${b.risk_weight}/100</div>
          <div style="font-size:0.75rem; color:#cbd5e1;">${b.safety_advice}</div>
        `);
        this.layers.blackspots.addLayer(circle);
      });
    }

    // 3. Render Responders
    if (data.responders) {
      this.layers.responders.clearLayers();
      data.responders.forEach(r => {
        const icon = L.divIcon({
          className: 'custom-pin pin-responder',
          html: `<span style="font-size:11px;font-weight:700;">🚔</span>`,
          iconSize: [26, 26],
          iconAnchor: [13, 13]
        });

        const marker = L.marker([r.current_latitude, r.current_longitude], { icon: icon });
        marker.bindPopup(`
          <div class="popup-title">${r.callsign}</div>
          <div class="popup-meta">Agency: ${r.agency_display} | Status: <b>${r.status_display}</b></div>
          <div style="font-size:0.75rem;">Officer: ${r.officer_in_charge} (${r.contact_number})</div>
        `);
        this.layers.responders.addLayer(marker);
        this.responderMarkers[r.id] = marker;
      });
    }

    // 4. Render Active SOS Alerts
    if (data.sos_alerts) {
      this.layers.sos.clearLayers();
      data.sos_alerts.forEach(sos => {
        this.addOrUpdateSosMarker(sos);
      });
    }

    // 5. Render CCTV Feeds
    if (data.camera_feeds) {
      this.layers.cameras.clearLayers();
      data.camera_feeds.forEach(cam => {
        const icon = L.divIcon({
          className: 'custom-pin pin-camera',
          html: `<span style="font-size:10px;">📹</span>`,
          iconSize: [22, 22],
          iconAnchor: [11, 11]
        });
        const marker = L.marker([cam.latitude, cam.longitude], { icon: icon });
        marker.bindPopup(`
          <div class="popup-title">${cam.camera_code}</div>
          <div class="popup-meta">${cam.location_name}</div>
          <a href="/ai-services/c2/" style="font-size:0.75rem; color:#38bdf8;">Inspect Vision AI Feed &rarr;</a>
        `);
        this.layers.cameras.addLayer(marker);
      });
    }
  }

  addOrUpdateSosMarker(sos) {
    const icon = L.divIcon({
      className: 'custom-pin pin-sos',
      html: `<span style="font-size:12px;font-weight:700;">SOS</span>`,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });

    if (this.activeSosMarkers[sos.sos_id]) {
      this.activeSosMarkers[sos.sos_id].setLatLng([sos.latitude, sos.longitude]);
    } else {
      const marker = L.marker([sos.latitude, sos.longitude], { icon: icon });
      marker.bindPopup(`
        <div class="popup-title" style="color:#ef4444;">EMERGENCY SOS: ${sos.sos_id}</div>
        <div class="popup-meta">Tourist: <b>${sos.tourist_name}</b> (${sos.tourist_phone})</div>
        <div style="font-size:0.75rem; margin-bottom:0.5rem;">Blood: ${sos.blood_group || 'N/A'} | Battery: ${sos.battery_level}%</div>
        <button onclick="window.c2Ops.openDispatchModal('${sos.sos_id}', ${sos.latitude}, ${sos.longitude})" class="btn btn-danger btn-sm" style="width:100%;">Dispatch Responders</button>
      `);
      this.layers.sos.addLayer(marker);
      this.activeSosMarkers[sos.sos_id] = marker;
    }
  }

  // --- Real-time WebSocket Feed ---
  initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/c2/stream/`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('C2 WebSocket Realtime Feed connected.');
        const statusDot = document.getElementById('c2-ws-status-dot');
        if (statusDot) statusDot.style.backgroundColor = '#10b981';
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleIncomingEvent(data);
        } catch (e) {}
      };

      this.ws.onclose = () => {
        const statusDot = document.getElementById('c2-ws-status-dot');
        if (statusDot) statusDot.style.backgroundColor = '#ef4444';
        setTimeout(() => this.initWebSocket(), 3000);
      };
    } catch (e) {
      console.warn('WebSocket connection error:', e);
    }
  }

  handleIncomingEvent(data) {
    if (data.type === 'new_sos_alert') {
      this.playAlertSound(920, 'sawtooth');
      if (data.sos) {
        this.addOrUpdateSosMarker(data.sos);
        this.map.flyTo([data.sos.latitude, data.sos.longitude], 14);
        this.prependSosCard(data.sos);
        this.incrementStat('hud-sos-count');
      }
    } else if (data.type === 'sos_breadcrumb_update') {
      if (this.activeSosMarkers[data.sos_id]) {
        this.activeSosMarkers[data.sos_id].setLatLng([data.latitude, data.longitude]);
      }
    } else if (data.type === 'sos_status_change') {
      if (data.status === 'CANCELLED' && this.activeSosMarkers[data.sos_id]) {
        this.layers.sos.removeLayer(this.activeSosMarkers[data.sos_id]);
        delete this.activeSosMarkers[data.sos_id];
      }
    }
  }

  prependSosCard(sos) {
    const container = document.getElementById('triage-sos-list');
    if (!container) return;

    const html = `
      <div class="c2-alert-card is-sos" id="sos-card-${sos.sos_id}">
        <div class="card-top-row">
          <span class="card-id-code">${sos.sos_id}</span>
          <span class="badge badge-critical">ACTIVE SOS</span>
        </div>
        <div class="card-headline">${sos.tourist_name}</div>
        <div class="card-meta-line">
          <span>📞 ${sos.tourist_phone}</span>
          <span>⚡ ${sos.battery_level}%</span>
        </div>
        <div class="card-actions-row">
          <button onclick="window.c2Ops.openDispatchModal('${sos.sos_id}', ${sos.latitude}, ${sos.longitude})" class="btn btn-danger btn-sm">Dispatch Unit</button>
          <button onclick="window.c2Ops.zoomToLocation(${sos.latitude}, ${sos.longitude})" class="btn btn-secondary btn-sm">Locate</button>
        </div>
      </div>
    `;
    container.insertAdjacentHTML('afterbegin', html);
  }

  incrementStat(id) {
    const el = document.getElementById(id);
    if (el) {
      const val = parseInt(el.innerText || '0', 10);
      el.innerText = val + 1;
    }
  }

  zoomToLocation(lat, lng) {
    if (this.map) {
      this.map.flyTo([lat, lng], 15);
    }
  }

  openDispatchModal(sosId, lat, lng) {
    const modal = document.getElementById('c2-dispatch-modal');
    const sosInput = document.getElementById('modal-dispatch-sos-id');
    if (modal && sosInput) {
      sosInput.value = sosId;
      modal.style.display = 'flex';
    }
  }

  initTriageTabs() {
    const btns = document.querySelectorAll('.triage-tab-btn');
    btns.forEach(btn => {
      btn.addEventListener('click', () => {
        btns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const tab = btn.getAttribute('data-tab');
        document.querySelectorAll('.triage-tab-content').forEach(c => c.style.display = 'none');
        const target = document.getElementById(`tab-content-${tab}`);
        if (target) target.style.display = 'flex';
      });
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  // Safe initialization guard: prevent collision with primary c2_command.html controller
  if (!window.tacticalMap && document.getElementById('c2-legacy-operations-map')) {
    window.c2Ops = new C2OperationsManager();
  }
});
