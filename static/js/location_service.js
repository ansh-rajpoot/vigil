/**
 * VIGIL LOCATION SERVICE MODULE
 * High-precision browser geolocation manager with single-marker Leaflet integration,
 * permission lifecycle handling, graceful error fallbacks, and throttled backend synchronization.
 */

class VigilLocationService {
  constructor(options = {}) {
    this.currentLat = null;
    this.currentLng = null;
    this.currentAccuracy = null;
    this.currentSpeed = 0.0;
    this.watchId = null;
    this.isTracking = false;
    this.lastBackendSyncTime = 0;
    this.lastSyncedLat = null;
    this.lastSyncedLng = null;
    this.map = null;
    this.userMarker = null;
    this.accuracyCircle = null;
    this.recenterControl = null;

    // Configurable thresholds
    this.minDistanceMetersForSync = options.minDistanceMeters || 10.0;
    this.minIntervalSecForSync = options.minIntervalSec || 15;
    this.backendSyncUrl = options.backendSyncUrl || '/tourist/api/location/';

    // Event callbacks
    this.onLocationChange = options.onLocationChange || null;
    this.onError = options.onError || null;
    this.onStatusChange = options.onStatusChange || null;
  }

  isSupported() {
    return 'geolocation' in navigator;
  }

  /**
   * One-time location request with full promise resolution and structured error codes.
   */
  async getCurrentPosition(options = {}) {
    if (!this.isSupported()) {
      const err = { code: 'NOT_SUPPORTED', message: 'Geolocation is not supported by this browser.' };
      if (this.onError) this.onError(err);
      throw err;
    }

    this._notifyStatus('ACQUIRING', 'Acquiring GPS position...');

    const geoOptions = {
      enableHighAccuracy: options.enableHighAccuracy !== undefined ? options.enableHighAccuracy : true,
      timeout: options.timeout || 10000,
      maximumAge: options.maximumAge || 10000
    };

    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const coords = this._processPosition(position);
          this._notifyStatus('LOCKED', `Position acquired (±${Math.round(coords.accuracy)}m)`);
          resolve(coords);
        },
        (error) => {
          const parsedError = this._handleGeoError(error);
          this._notifyStatus('ERROR', parsedError.message);
          if (this.onError) this.onError(parsedError);
          reject(parsedError);
        },
        geoOptions
      );
    });
  }

  /**
   * Continuous location tracking using navigator.geolocation.watchPosition
   */
  startTracking(mapInstance = null, options = {}) {
    if (!this.isSupported()) {
      if (this.onError) this.onError({ code: 'NOT_SUPPORTED', message: 'Geolocation not supported.' });
      return;
    }

    if (mapInstance) {
      this.attachToMap(mapInstance, options);
    }

    if (this.isTracking) return;

    this._notifyStatus('TRACKING', 'Live GPS tracking active...');
    this.isTracking = true;

    const geoOptions = {
      enableHighAccuracy: true,
      timeout: 12000,
      maximumAge: 5000
    };

    this.watchId = navigator.geolocation.watchPosition(
      (position) => {
        const coords = this._processPosition(position);
        this.updateMapMarker(coords.latitude, coords.longitude, coords.accuracy);
        this.syncWithBackendIfNecessary(coords);
      },
      (error) => {
        const parsedError = this._handleGeoError(error);
        this._notifyStatus('ERROR', parsedError.message);
        if (this.onError) this.onError(parsedError);
      },
      geoOptions
    );
  }

  stopTracking() {
    if (this.watchId !== null) {
      navigator.geolocation.clearWatch(this.watchId);
      this.watchId = null;
    }
    this.isTracking = false;
    this._notifyStatus('STOPPED', 'Location tracking stopped.');
  }

  /**
   * Leaflet Map Attachment: Single persistent custom marker + accuracy circle + Recenter control.
   */
  attachToMap(mapInstance, options = {}) {
    this.map = mapInstance;
    const shouldCenterOnFirstLock = options.autoCenter !== false;

    // Create Recenter Control button if not existing
    if (!this.recenterControl && this.map) {
      const RecenterControl = L.Control.extend({
        options: { position: 'topright' },
        onAdd: () => {
          const btn = L.DomUtil.create('button', 'leaflet-bar vigil-recenter-btn');
          btn.title = 'Recenter on my location';
          btn.innerHTML = `
            <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; padding:6px 10px; box-shadow:0 2px 6px rgba(0,0,0,0.15); display:flex; align-items:center; gap:6px; font-family:Inter,sans-serif; font-size:12px; font-weight:600; color:#0f172a; cursor:pointer;">
              <span style="font-size:14px;">📍</span>
              <span id="vigil-recenter-label">My Location</span>
            </div>
          `;
          btn.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.recenter();
          };
          return btn;
        }
      });
      this.recenterControl = new RecenterControl();
      this.recenterControl.addTo(this.map);
    }

    // If we already have coordinates, render immediately
    if (this.currentLat && this.currentLng) {
      this.updateMapMarker(this.currentLat, this.currentLng, this.currentAccuracy);
      if (shouldCenterOnFirstLock) {
        this.recenter();
      }
    }
  }

  /**
   * Updates existing marker & circle instead of creating duplicates.
   */
  updateMapMarker(lat, lng, accuracy = 10) {
    if (!this.map) return;

    const icon = L.divIcon({
      className: 'vigil-user-pulse-marker',
      html: `
        <div style="position:relative; width:22px; height:22px;">
          <div style="position:absolute; inset:-4px; background:rgba(16, 185, 129, 0.35); border-radius:50%; animation:vigilPulse 2s infinite ease-out;"></div>
          <div style="position:absolute; inset:0; background:#059669; border:2.5px solid #ffffff; border-radius:50%; box-shadow:0 2px 6px rgba(0,0,0,0.3);"></div>
        </div>
      `,
      iconSize: [22, 22],
      iconAnchor: [11, 11],
      popupAnchor: [0, -12]
    });

    if (this.userMarker) {
      this.userMarker.setLatLng([lat, lng]);
    } else {
      this.userMarker = L.marker([lat, lng], { icon: icon, zIndexOffset: 1000 });
      this.userMarker.bindPopup(`
        <div style="font-family:Inter,sans-serif; min-width:160px; font-size:12px;">
          <div style="font-weight:700; color:#059669; text-transform:uppercase; font-size:11px;">📍 Your Current Location</div>
          <div style="color:#0f172a; margin-top:3px; font-weight:600;">${lat.toFixed(5)}, ${lng.toFixed(5)}</div>
          <div style="color:#64748b; font-size:11px; margin-top:2px;">Accuracy: ±${Math.round(accuracy)}m</div>
        </div>
      `);
      this.userMarker.addTo(this.map);
    }

    if (this.accuracyCircle) {
      this.accuracyCircle.setLatLng([lat, lng]);
      this.accuracyCircle.setRadius(Math.max(accuracy, 15));
    } else {
      this.accuracyCircle = L.circle([lat, lng], {
        radius: Math.max(accuracy, 15),
        color: '#10b981',
        weight: 1,
        fillColor: '#10b981',
        fillOpacity: 0.12
      }).addTo(this.map);
    }
  }

  /**
   * Smoothly pans the map to current user coordinates.
   */
  recenter(zoom = 15) {
    if (this.map && this.currentLat && this.currentLng) {
      this.map.flyTo([this.currentLat, this.currentLng], zoom, { animate: true, duration: 1.0 });
    } else {
      // If not yet available, trigger a fresh request
      this.getCurrentPosition().then(coords => {
        if (this.map) {
          this.map.flyTo([coords.latitude, coords.longitude], zoom, { animate: true, duration: 1.0 });
        }
      }).catch(() => {});
    }
  }

  /**
   * Throttled backend sync: only transmits when moved > minDistanceMeters OR > minIntervalSec elapsed.
   */
  async syncWithBackendIfNecessary(coords) {
    const nowSec = Math.floor(Date.now() / 1000);
    const timeElapsed = nowSec - this.lastBackendSyncTime;

    let distanceMovedMeters = 99999;
    if (this.lastSyncedLat !== null && this.lastSyncedLng !== null) {
      distanceMovedMeters = this._calculateHaversineMeters(
        this.lastSyncedLat, this.lastSyncedLng,
        coords.latitude, coords.longitude
      );
    }

    if (timeElapsed >= this.minIntervalSecForSync || distanceMovedMeters >= this.minDistanceMetersForSync) {
      await this.pushLocationToBackend(coords);
    }
  }

  async pushLocationToBackend(coords) {
    let batteryLevel = 90;
    try {
      if ('getBattery' in navigator) {
        const b = await navigator.getBattery();
        batteryLevel = Math.round(b.level * 100);
      }
    } catch (e) {}

    try {
      const csrfToken = this._getCSRFToken();
      const payload = {
        latitude: coords.latitude,
        longitude: coords.longitude,
        accuracy: coords.accuracy || 5.0,
        speed: coords.speed || 0.0,
        battery_level: batteryLevel
      };

      const res = await fetch(this.backendSyncUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (data.success) {
        this.lastBackendSyncTime = Math.floor(Date.now() / 1000);
        this.lastSyncedLat = coords.latitude;
        this.lastSyncedLng = coords.longitude;
      }
    } catch (err) {
      console.warn('VIGIL Location sync warning:', err);
    }
  }

  _processPosition(position) {
    this.currentLat = position.coords.latitude;
    this.currentLng = position.coords.longitude;
    this.currentAccuracy = position.coords.accuracy;
    this.currentSpeed = position.coords.speed || 0.0;

    const coords = {
      latitude: this.currentLat,
      longitude: this.currentLng,
      accuracy: this.currentAccuracy,
      speed: this.currentSpeed,
      timestamp: position.timestamp
    };

    if (this.onLocationChange) {
      this.onLocationChange(coords);
    }

    return coords;
  }

  _handleGeoError(error) {
    let code = 'UNKNOWN_ERROR';
    let message = 'An unknown geolocation error occurred.';

    switch (error.code) {
      case error.PERMISSION_DENIED:
        code = 'PERMISSION_DENIED';
        message = 'Location access permission was denied by the user. Please enable location permissions in browser settings.';
        break;
      case error.POSITION_UNAVAILABLE:
        code = 'POSITION_UNAVAILABLE';
        message = 'GPS or network position information is currently unavailable.';
        break;
      case error.TIMEOUT:
        code = 'TIMEOUT';
        message = 'The request to acquire geolocation timed out.';
        break;
    }

    return { code, message, originalError: error };
  }

  _notifyStatus(status, message) {
    if (this.onStatusChange) {
      this.onStatusChange(status, message);
    }
  }

  _calculateHaversineMeters(lat1, lon1, lat2, lon2) {
    const R = 6371000; // meters
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  _getCSRFToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
  }

  formatCoords(lat = this.currentLat, lng = this.currentLng) {
    if (lat === null || lng === null) return 'Location unavailable';
    const latDir = lat >= 0 ? 'N' : 'S';
    const lngDir = lng >= 0 ? 'E' : 'W';
    return `${Math.abs(lat).toFixed(4)}° ${latDir}, ${Math.abs(lng).toFixed(4)}° ${lngDir}`;
  }
}

// Global singleton instance
window.vigilLocation = new VigilLocationService();
