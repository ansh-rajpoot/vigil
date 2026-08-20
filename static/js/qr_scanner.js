/**
 * VIGIL PUBLIC / POLICE QR VERIFICATION SCANNER
 * Live camera feed scanner and manual ID validator for checkpoints.
 */

class QRVerificationController {
  constructor() {
    this.videoStream = null;
    this.videoEl = document.getElementById('qr-scanner-video');
    this.init();
  }

  init() {
    this.initManualForm();
    this.initCameraToggle();
    this.checkUrlParams();
  }

  checkUrlParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const idParam = urlParams.get('id');
    const tokenParam = urlParams.get('token');

    if (idParam) {
      const idInput = document.getElementById('verify-id-input');
      const tokenInput = document.getElementById('verify-totp-input');
      if (idInput) idInput.value = idParam;
      if (tokenInput && tokenParam) tokenInput.value = tokenParam;

      this.executeVerification({
        id_number: idParam,
        totp_code: tokenParam || '',
        verifier_name: document.getElementById('verifier-name')?.value || 'Tourism Police Officer',
        verifier_role: 'Tourism Police Checkpoint',
        location_name: document.getElementById('verifier-location')?.value || 'Checkpoint North'
      });
    }
  }

  initManualForm() {
    const form = document.getElementById('manual-verify-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const idCode = document.getElementById('verify-id-input').value.trim();
      const totpCode = document.getElementById('verify-totp-input')?.value.trim();

      if (!idCode) return;

      this.executeVerification({
        id_number: idCode,
        totp_code: totpCode,
        verifier_name: document.getElementById('verifier-name')?.value || 'Tourism Police Officer',
        verifier_role: 'Tourism Police Checkpoint',
        location_name: document.getElementById('verifier-location')?.value || 'Checkpoint North'
      });
    });
  }

  initCameraToggle() {
    const startBtn = document.getElementById('btn-start-camera');
    const stopBtn = document.getElementById('btn-stop-camera');

    if (startBtn) {
      startBtn.addEventListener('click', () => this.startCamera());
    }
    if (stopBtn) {
      stopBtn.addEventListener('click', () => this.stopCamera());
    }
  }

  async startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert('Camera access is not supported by your browser.');
      return;
    }

    try {
      this.videoStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      });
      if (this.videoEl) {
        this.videoEl.srcObject = this.videoStream;
        this.videoEl.style.display = 'block';
        document.getElementById('scanner-placeholder').style.display = 'none';
      }
    } catch (err) {
      alert('Unable to access camera on this device. Please enter ID code manually or use fast demo buttons.');
    }
  }

  stopCamera() {
    if (this.videoStream) {
      this.videoStream.getTracks().forEach(track => track.stop());
      this.videoStream = null;
    }
    if (this.videoEl) this.videoEl.style.display = 'none';
    const placeholder = document.getElementById('scanner-placeholder');
    if (placeholder) placeholder.style.display = 'flex';
  }

  async executeVerification(payload) {
    const resultBox = document.getElementById('verification-result-box');
    const submitBtn = document.getElementById('btn-submit-verify');

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerText = 'Verifying Authenticity...';
    }

    try {
      const res = await fetch('/digital-id/api/verify/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (resultBox) {
        resultBox.style.display = 'block';
        this.renderResultCard(resultBox, data);
        resultBox.scrollIntoView({ behavior: 'smooth' });
      }
    } catch (err) {
      alert('Verification server request failed.');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerText = 'Verify Digital Tourist ID';
      }
    }
  }

  renderResultCard(container, response) {
    const isSuccess = response.success;
    const info = response.data || {};

    const badgeClass = info.verification_result === 'VALID' ? 'badge-safe' :
                       info.verification_result === 'FLAGGED_ALERT' ? 'badge-critical' : 'badge-warning';

    container.innerHTML = `
      <div class="card" style="border-top: 4px solid ${isSuccess ? '#059669' : '#dc2626'}; margin-top: 1.5rem; animation: fadeIn 0.3s ease;">
        <div class="card-header">
          <div style="display:flex; align-items:center; gap:0.5rem;">
            <span style="font-size:1.25rem;">${isSuccess ? '✅' : '⚠️'}</span>
            <span class="card-title">${isSuccess ? 'AUTHENTIC DIGITAL TOURIST ID' : 'VERIFICATION ALERT'}</span>
          </div>
          <span class="badge ${badgeClass}">${info.verification_result || 'UNKNOWN'}</span>
        </div>
        <div class="card-body">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
            <div>
              <div style="font-size:0.75rem; color:#64748b;">Tourist Name</div>
              <div style="font-size:1.125rem; font-weight:700; color:#0f172a;">${info.tourist_name || 'Unknown'}</div>
            </div>
            <div>
              <div style="font-size:0.75rem; color:#64748b;">Digital ID Number</div>
              <div style="font-family:monospace; font-weight:700; font-size:1rem; color:#1e3a8a;">${info.id_number || 'N/A'}</div>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; background:#f8fafc; padding:0.75rem; border-radius:6px; border:1px solid #e2e8f0; margin-bottom: 1rem;">
            <div>
              <div style="font-size:0.6875rem; color:#64748b;">Nationality</div>
              <div style="font-weight:600; font-size:0.875rem;">${info.nationality || 'Indian'}</div>
            </div>
            <div>
              <div style="font-size:0.6875rem; color:#64748b;">Blood Group</div>
              <div style="font-weight:600; font-size:0.875rem; color:#dc2626;">${info.blood_group || 'N/A'}</div>
            </div>
            <div>
              <div style="font-size:0.6875rem; color:#64748b;">Token Signature</div>
              <div style="font-weight:600; font-size:0.875rem; color:#059669;">${info.token_verified ? 'Verified (TOTP Valid)' : 'Unverified'}</div>
            </div>
          </div>

          <div style="margin-bottom: 0.75rem;">
            <div style="font-size:0.75rem; color:#64748b; margin-bottom:0.25rem;">Stay / Accommodation Details:</div>
            <div style="font-size:0.875rem; font-weight:500; color:#334155;">${info.hotel_stay_details || 'Verified registered tourist'}</div>
          </div>

          ${info.emergency_contacts && info.emergency_contacts.length > 0 ? `
          <div style="border-top: 1px solid #e2e8f0; padding-top: 0.75rem; margin-top: 0.75rem;">
            <div style="font-size:0.75rem; color:#64748b; margin-bottom:0.25rem;">Primary Emergency Contact:</div>
            <div style="font-size:0.875rem; font-weight:600; color:#0f172a;">
              ${info.emergency_contacts[0].name} (${info.emergency_contacts[0].rel}) • <span style="color:#1e3a8a;">${info.emergency_contacts[0].phone}</span>
            </div>
          </div>
          ` : ''}
        </div>
        <div class="card-footer" style="display:flex; justify-content:space-between; font-size:0.75rem; color:#64748b;">
          <span>Official GovTech Security Protocol 3.4</span>
          <span>Verified: ${info.verified_at || 'Just now'}</span>
        </div>
      </div>
    `;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.qrScanner = new QRVerificationController();
});
