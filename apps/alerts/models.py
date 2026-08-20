import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from common.utils import haversine_distance


class EmergencyBroadcast(models.Model):
    ALERT_TYPE_CHOICES = (
        ('DISASTER', 'Natural Disaster (Evacuation / Surge)'),
        ('SEVERE_WEATHER', 'Severe Weather / High Waves Warning'),
        ('CRIME_ACTIVITY', 'Crime Activity / Heightened Vigilance'),
        ('ACCIDENT', 'Traffic Collision / Road Obstruction'),
        ('CROWD_EMERGENCY', 'Crowd Emergency / Stampede Risk'),
        ('RESTRICTED_AREA', 'Restricted Perimeter / Prohibited Zone'),
        ('GENERAL_SAFETY', 'General Safety Advisory'),
    )

    SEVERITY_CHOICES = (
        ('CRITICAL', 'Critical Emergency (Immediate Action Required)'),
        ('WARNING', 'Warning (Heightened Vigilance)'),
        ('ADVISORY', 'Advisory (General Information)'),
    )

    TARGET_TYPE_CHOICES = (
        ('ALL_TOURISTS', 'All Active Tourists in Region'),
        ('ZONE_SPECIFIC', 'Tourists inside Specific Geofence Zone'),
        ('GEO_RADIUS', 'Tourists within Geographic Radius'),
    )

    broadcast_code = models.CharField(max_length=32, unique=True, db_index=True)
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES, default='GENERAL_SAFETY')
    title = models.CharField(max_length=200)
    message = models.TextField(help_text="Detailed safety advisory and instructions for tourists")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='WARNING')
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES, default='ALL_TOURISTS')

    target_zone = models.ForeignKey('geofencing.GeoZone', null=True, blank=True, on_delete=models.SET_NULL, related_name='broadcasts')
    center_latitude = models.FloatField(null=True, blank=True)
    center_longitude = models.FloatField(null=True, blank=True)
    radius_meters = models.IntegerField(null=True, blank=True, help_text="Impact radius in meters")

    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.broadcast_code:
            self.broadcast_code = f"BRD-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_currently_active(self) -> bool:
        now = timezone.now()
        if not self.is_active:
            return False
        if self.starts_at and self.starts_at > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True

    def applies_to_location(self, lat: float, lng: float) -> bool:
        """Determines if the broadcast applies to coordinates."""
        if not self.is_currently_active():
            return False
        if self.target_type == 'ALL_TOURISTS':
            return True
        if self.target_type == 'ZONE_SPECIFIC' and self.target_zone:
            return self.target_zone.contains_point(lat, lng)
        if self.target_type == 'GEO_RADIUS' and self.center_latitude and self.center_longitude and self.radius_meters:
            dist_km = haversine_distance(lat, lng, self.center_latitude, self.center_longitude)
            return (dist_km * 1000.0) <= float(self.radius_meters)
        return True

    def get_color_theme(self) -> dict:
        """Returns standard UI colors for clean, non-chaotic rendering."""
        if self.severity == 'CRITICAL':
            return {'bg': '#fef2f2', 'border': '#ef4444', 'text': '#991b1b', 'badge': 'badge-critical', 'icon': '🚨'}
        elif self.severity == 'WARNING':
            return {'bg': '#fffbeb', 'border': '#f59e0b', 'text': '#92400e', 'badge': 'badge-warning', 'icon': '⚠️'}
        else:
            return {'bg': '#f8fafc', 'border': '#38bdf8', 'text': '#0369a1', 'badge': 'badge-safe', 'icon': 'ℹ️'}

    def __str__(self):
        return f"{self.broadcast_code} [{self.get_severity_display()}] - {self.title}"


class AlertReceipt(models.Model):
    broadcast = models.ForeignKey(EmergencyBroadcast, on_delete=models.CASCADE, related_name='receipts')
    tourist = models.ForeignKey('tourists.TouristProfile', on_delete=models.CASCADE, related_name='alert_receipts')
    delivered_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('broadcast', 'tourist')
        ordering = ['-delivered_at']

    def __str__(self):
        return f"Receipt {self.broadcast.broadcast_code} -> {self.tourist.user.username}"
