from django.db import models
from django.conf import settings
from django.utils import timezone
from common.utils import point_in_polygon


class GeoZone(models.Model):
    ZONE_TYPE_CHOICES = (
        ('SAFE', 'Safe Zone / Designated Haven'),
        ('CAUTION', 'Caution Zone / Heightened Vigilance'),
        ('HIGH_RISK', 'High Risk Hazard Zone'),
        ('RESTRICTED', 'Restricted Area / No Entry'),
        ('EMERGENCY', 'Emergency Disaster Evacuation Zone'),
    )

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    zone_type = models.CharField(max_length=30, choices=ZONE_TYPE_CHOICES, default='CAUTION')
    description = models.TextField(blank=True)
    polygon_geojson = models.JSONField(help_text="GeoJSON Polygon geometry with coordinates array")
    center_latitude = models.FloatField()
    center_longitude = models.FloatField()
    radius_meters = models.IntegerField(default=500, help_text="Approximate radius in meters")
    is_active = models.BooleanField(default=True)
    curfew_start_time = models.TimeField(null=True, blank=True)
    curfew_end_time = models.TimeField(null=True, blank=True)
    max_crowd_threshold = models.IntegerField(default=500)
    safety_advisory = models.TextField(blank=True, help_text="Safety warning delivered to tourists when entering")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def contains_point(self, lat: float, lng: float) -> bool:
        """Determines if (lat, lng) falls within the GeoJSON polygon boundary."""
        return point_in_polygon(lat, lng, self.polygon_geojson)

    def is_curfew_active_now(self) -> bool:
        if not self.curfew_start_time or not self.curfew_end_time:
            return False
        now_time = timezone.localtime().time()
        if self.curfew_start_time <= self.curfew_end_time:
            return self.curfew_start_time <= now_time <= self.curfew_end_time
        else:  # Overnight curfew (e.g. 22:00 to 06:00)
            return now_time >= self.curfew_start_time or now_time <= self.curfew_end_time

    def get_color_hex(self) -> str:
        """Returns standard visual status color for Leaflet rendering."""
        color_map = {
            'SAFE': '#10b981',        # Green
            'CAUTION': '#f59e0b',     # Amber
            'HIGH_RISK': '#ea580c',   # Orange
            'RESTRICTED': '#dc2626',  # Red / Crimson
            'EMERGENCY': '#ef4444',   # Red / Critical
        }
        return color_map.get(self.zone_type, '#64748b')

    def __str__(self):
        return f"{self.name} [{self.get_zone_type_display()}]"


class TouristZonePresence(models.Model):
    """
    Active geofence state tracker per tourist.
    Prevents repeated duplicate alerts when a tourist remains inside the same zone.
    """
    tourist = models.ForeignKey('tourists.TouristProfile', on_delete=models.CASCADE, related_name='active_zone_presences')
    zone = models.ForeignKey(GeoZone, on_delete=models.CASCADE, related_name='current_occupants')
    entered_at = models.DateTimeField(auto_now_add=True)
    last_detected_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    alert_dispatched = models.BooleanField(default=True)
    authority_notified = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['tourist', 'zone', 'is_active']),
        ]

    def __str__(self):
        return f"{self.tourist.user.username} in {self.zone.name} (Active: {self.is_active})"


class GeofenceBreachLog(models.Model):
    BREACH_TYPE_CHOICES = (
        ('ENTRY_SAFE', 'Entered Safe Haven Zone'),
        ('ENTRY_CAUTION', 'Entered Caution Zone'),
        ('ENTER_RESTRICTED', 'Entered Restricted Zone'),
        ('ENTER_DANGER', 'Entered High-Risk Hazard Zone'),
        ('ENTER_EMERGENCY', 'Entered Emergency Evacuation Zone'),
        ('CURFEW_VIOLATION', 'Curfew Hours Violation'),
        ('ZONE_EXIT', 'Exited Geofence Zone'),
    )

    tourist = models.ForeignKey('tourists.TouristProfile', on_delete=models.CASCADE, related_name='breach_logs')
    zone = models.ForeignKey(GeoZone, on_delete=models.CASCADE, related_name='breaches')
    breach_type = models.CharField(max_length=30, choices=BREACH_TYPE_CHOICES)
    latitude = models.FloatField()
    longitude = models.FloatField()
    risk_score_after = models.IntegerField(default=15)
    authority_notified = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action_taken = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.tourist.user.username} - {self.zone.name} ({self.get_breach_type_display()})"
