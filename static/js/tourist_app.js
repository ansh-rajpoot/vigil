/**
 * VIGIL TOURIST APPLICATION CONTROLLER
 * Handles Digital ID rotation, safety check-ins, SOS countdown triggers, and GPS sync.
 */

class TouristApp {
  constructor() {
    this.countdownTimer = null;
    this.countdownSeconds = 5;
    this.isSosCountdownActive = false;
    this.totpSecondsRemaining = 30;
    this.init();
  }

  init() {
    this.initDigitalIDCard();
    this.initTotpTimer();
    this.initSosTrigger();
    this.initSafetyCheckin();
    this.initGpsHeartbeat();
  }

  // --- Digital ID Flip & Interactive Card ---
  initDigitalIDCard() {
    const card = document.getElementById('digital-id-card');
    const flipBtn = document.getElementById('flip-id-btn');

    if (card) {
      card.addEventListener('click', (e) => {
        // Prevent flip if clicking directly on a button inside
        if (e.target.tagName === 'BUTTON' || e.target.closest('button')) return;
        card.classList.toggle('is-flipped');
      });
    }

    if (flipBtn && card) {
      flipBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        card.classList.toggle('is-flipped');
      });
    }
  }

  // --- Dynamic Rotating TOTP & QR Refresher ---
  initTotpTimer() {
    const totpEl = document.getElementById('dynamic-totp-val');
    const timerProgressEl = document.getElementById('totp-timer-progress');
    const qrImgEl = document.getElementById('dynamic-qr-img');

    if (!totpEl) return;

    setInterval(() => {
      this.totpSecondsRemaining--;
      if (timerProgressEl) {
        const pct = (this.totpSecondsRemaining / 30) * 100;
        timerProgressEl.style.width = `${pct}%`;
      }

      if (this.totpSecondsRemaining <= 0) {
        this.totpSecondsRemaining = 30;
        this.refreshDynamicQR(totpEl, qrImgEl);
      }
    }, 1000);
  }

  async refreshDynamicQR(totpEl, qrImgEl) {
    try {
      const res = await fetch('/digital-id/api/dynamic-qr/');
      const data = await res.json();
      if (data.success && data.data) {
        if (totpEl) totpEl.innerText = data.data.payload.totp;
        if (qrImgEl && data.data.qr_image_url) {
          qrImgEl.src = `${data.data.qr_image_url}?t=${new Date().getTime()}`;
        }
      }
    } catch (err) {
      console.warn('Dynamic QR auto-refresh:', err);
    }
  }

  // --- Tactical SOS Panic Trigger with 5s Buffer Countdown ---
  initSosTrigger() {
    const sosBtns = document.querySelectorAll('.js-sos-trigger');
    const modal = document.getElementById('sos-countdown-modal');
    const countNum = document.getElementById('sos-count-num');
    const cancelBtn = document.getElementById('sos-cancel-countdown-btn');
    const confirmNowBtn = document.getElementById('sos-instant-confirm-btn');

    sosBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        this.openSosCountdown(modal, countNum);
      });
    });

    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => {
        this.abortSosCountdown(modal);
      });
    }

    if (confirmNowBtn) {
      confirmNowBtn.addEventListener('click', () => {
        this.dispatchSosEmergency(modal);
      });
    }
  }

  openSosCountdown(modal, countNum) {
    if (!modal) return;
    modal.style.display = 'flex';
    this.countdownSeconds = 5;
    if (countNum) countNum.innerText = this.countdownSeconds;
    this.isSosCountdownActive = true;

    // Vibrate if mobile device supported
    if ('vibrate' in navigator) {
      navigator.vibrate([200, 100, 200]);
    }

    clearInterval(this.countdownTimer);
    this.countdownTimer = setInterval(() => {
      this.countdownSeconds--;
      if (countNum) countNum.innerText = this.countdownSeconds;

      if (this.countdownSeconds <= 0) {
        clearInterval(this.countdownTimer);
        this.dispatchSosEmergency(modal);
      }
    }, 1000);
  }

  abortSosCountdown(modal) {
    clearInterval(this.countdownTimer);
    this.isSosCountdownActive = false;
    if (modal) modal.style.display = 'none';
  }

  async dispatchSosEmergency(modal) {
    clearInterval(this.countdownTimer);
    if (modal) modal.style.display = 'none';

    let lat = 15.4989;
    let lng = 73.8278;
    let accuracy = 5.0;

    // Use VigilLocationService to acquire real high-accuracy position
    if (window.vigilLocation && window.vigilLocation.isSupported()) {
      try {
        const pos = await window.vigilLocation.getCurrentPosition({ timeout: 5000, enableHighAccuracy: true });
        lat = pos.latitude;
        lng = pos.longitude;
        accuracy = pos.accuracy;
      } catch (e) {
        if (window.vigilLocation.currentLat && window.vigilLocation.currentLng) {
          lat = window.vigilLocation.currentLat;
          lng = window.vigilLocation.currentLng;
          accuracy = window.vigilLocation.currentAccuracy || 10.0;
        }
        console.warn('Geolocation acquisition status for SOS:', e);
      }
    }

    try {
      const res = await fetch('/emergency/api/trigger/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        },
        body: JSON.stringify({
          latitude: lat,
          longitude: lng,
          accuracy: accuracy,
          trigger_type: 'MANUAL_BUTTON',
          battery_level: 90
        })
      });

      const data = await res.json();
      if (data.success && data.data) {
        window.location.href = `/emergency/active/${data.data.sos_id}/`;
      } else {
        alert(data.message || 'Error triggering SOS');
      }
    } catch (err) {
      alert('Network error initiating emergency beacon.');
    }
  }

  // --- Safe Check-in ---
  initSafetyCheckin() {
    const checkinBtn = document.getElementById('safe-checkin-btn');
    if (!checkinBtn) return;

    checkinBtn.addEventListener('click', async () => {
      checkinBtn.disabled = true;
      checkinBtn.innerText = 'Checking In...';

      try {
        const res = await fetch('/tourist/api/checkin/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCSRFToken()
          }
        });
        const data = await res.json();
        if (data.success) {
          checkinBtn.innerText = '✓ Safe Check-in Recorded';
          checkinBtn.classList.remove('btn-secondary');
          checkinBtn.classList.add('btn-safe');
          setTimeout(() => {
            checkinBtn.innerText = 'Safe Check-in';
            checkinBtn.classList.remove('btn-safe');
            checkinBtn.classList.add('btn-secondary');
            checkinBtn.disabled = false;
          }, 4000);
        }
      } catch (e) {
        checkinBtn.innerText = 'Safe Check-in';
        checkinBtn.disabled = false;
      }
    });
  }

  // --- GPS Heartbeat Auto-Sync via VigilLocationService ---
  initGpsHeartbeat() {
    if (window.vigilLocation && window.vigilLocation.isSupported()) {
      window.vigilLocation.startTracking(null, { autoCenter: false });
    }
  }

  getCSRFToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
  }
}

async function toggleNavAlertsPanel() {
  const panel = document.getElementById('nav-alerts-panel');
  if (!panel) return;

  const isVisible = panel.style.display === 'block';
  panel.style.display = isVisible ? 'none' : 'block';

  if (!isVisible) {
    const content = document.getElementById('nav-alerts-content');
    try {
      const res = await fetch('/alerts/api/?active=true');
      const data = await res.json();
      if (data.success && data.data) {
        if (data.data.length === 0) {
          content.innerHTML = '<div style="font-size:0.75rem; color:#64748b; text-align:center; padding:1rem;">No active emergency alerts in your sector.</div>';
        } else {
          content.innerHTML = data.data.map(a => `
            <div style="background:${a.theme.bg}; border-left:3px solid ${a.theme.border}; padding:0.5rem 0.65rem; border-radius:4px; font-size:0.75rem;">
              <div style="font-weight:700; color:${a.theme.text}; margin-bottom:0.15rem;">
                ${a.theme.icon} ${a.alert_type_display}: ${a.title}
              </div>
              <div style="color:#334155; line-height:1.35; margin-bottom:0.3rem;">${a.message}</div>
              <div style="font-size:0.6875rem; color:#64748b;">Target: <b>${a.zone_name}</b></div>
            </div>
          `).join('');
        }
      }
    } catch (e) {
      content.innerHTML = '<div style="font-size:0.75rem; color:#ef4444; text-align:center; padding:1rem;">Failed to load alerts feed.</div>';
    }
  }
}

// Close alert dropdown when clicking outside
document.addEventListener('click', (e) => {
  const panel = document.getElementById('nav-alerts-panel');
  const btn = document.getElementById('nav-alerts-bell-btn');
  if (panel && btn && panel.style.display === 'block') {
    if (!panel.contains(e.target) && !btn.contains(e.target)) {
      panel.style.display = 'none';
    }
  }
});

document.addEventListener('DOMContentLoaded', () => {
  window.touristApp = new TouristApp();
});
