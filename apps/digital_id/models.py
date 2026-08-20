import io
import json
import base64
import qrcode
from PIL import Image, ImageDraw
from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from common.utils import generate_dynamic_totp_token, generate_secure_crypto_hash


class DigitalTouristID(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Verified & Active'),
        ('FLAGGED', 'Security Watchlist / Flagged'),
        ('SUSPENDED', 'Temporarily Suspended'),
        ('EXPIRED', 'Expired Validity'),
    )

    tourist = models.OneToOneField('tourists.TouristProfile', on_delete=models.CASCADE, related_name='digital_id')
    id_number = models.CharField(max_length=32, unique=True, db_index=True)
    crypto_hash = models.CharField(max_length=128)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    issued_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField()
    verification_token_secret = models.CharField(max_length=64)
    qr_code_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    def is_valid(self):
        if self.status != 'ACTIVE':
            return False
        if timezone.now() > self.valid_until:
            return False
        return True

    def get_current_totp(self):
        """Generates real-time 6-digit TOTP token using 30-second steps."""
        return generate_dynamic_totp_token(self.verification_token_secret, step=30)

    def get_qr_payload_dict(self):
        """
        Generates secure verification payload for QR encoding.
        Contains strictly verification identifiers, dynamic TOTP, and cryptographic signature.
        Avoids embedding raw unencrypted private information.
        """
        totp = self.get_current_totp()
        timestamp = int(timezone.now().timestamp())
        sig = generate_secure_crypto_hash(f"{self.id_number}:{totp}:{self.verification_token_secret}")[:16]

        payload = {
            "v_id": self.id_number,
            "totp": totp,
            "ts": timestamp,
            "sig": sig,
            "verify_url": f"/digital-id/verify/?id={self.id_number}&token={totp}"
        }
        return payload

    def generate_qr_code(self):
        """Generates a crisp, high-resolution QR code image encoding the secure verification payload."""
        payload_data = json.dumps(self.get_qr_payload_dict())
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(payload_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        file_name = f"qr_{self.id_number}.png"
        self.qr_code_image.save(file_name, ContentFile(buffer.getvalue()), save=False)
        self.save(update_fields=['qr_code_image'])

    def __str__(self):
        return f"{self.id_number} - {self.tourist.user.username} ({self.get_status_display()})"


class IDVerificationLog(models.Model):
    digital_id = models.ForeignKey(DigitalTouristID, on_delete=models.CASCADE, related_name='verification_logs')
    verifier_name = models.CharField(max_length=150, help_text="Officer or Scanner operator name")
    verifier_role = models.CharField(max_length=50, default='Tourism Police')
    verifier_badge = models.CharField(max_length=50, blank=True)
    location_name = models.CharField(max_length=150, default='Checkpoint Alpha')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    status_result = models.CharField(max_length=30, default='VALID')
    verification_notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Scan {self.digital_id.id_number} by {self.verifier_name} - {self.status_result}"
