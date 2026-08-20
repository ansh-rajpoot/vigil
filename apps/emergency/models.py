import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class ResponderUnit(models.Model):
    AGENCY_CHOICES = (
        ('POLICE', 'Police Patrol / PCR Van'),
        ('TOURISM_POLICE', 'Tourism Police Task Force'),
        ('AMBULANCE', '108 Ambulance / Medical EMS'),
        ('FIRE_RESCUE', 'Fire & Disaster Rescue'),
        ('BEACH_LIFEGUARD', 'Coast Guard / Beach Lifeguards'),
    )

    STATUS_CHOICES = (
        ('AVAILABLE', 'Available / On Patrol'),
        ('DISPATCHED', 'Dispatched / En Route'),
        ('ON_SCENE', 'On Scene / Engaged'),
        ('OFF_DUTY', 'Off Duty / Inactive'),
    )

    unit_code = models.CharField(max_length=50, unique=True, db_index=True)
    agency = models.CharField(max_length=30, choices=AGENCY_CHOICES, default='POLICE')
    callsign = models.CharField(max_length=100, help_text="e.g. PCR-PANJIM-04, LIFEGUARD-CALANGUTE")
    officer_in_charge = models.CharField(max_length=150)
    contact_number = models.CharField(max_length=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')

    current_latitude = models.FloatField()
    current_longitude = models.FloatField()
    station_base_name = models.CharField(max_length=150, blank=True)
    assigned_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='responder_profile')
    last_heartbeat = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.callsign} ({self.get_agency_display()}) - [{self.get_status_display()}]"


class SOSAlert(models.Model):
    TRIGGER_CHOICES = (
        ('MANUAL_BUTTON', 'SOS Panic Button Tap'),
        ('COUNTDOWN_TRIGGER', 'Countdown Timer Expired'),
        ('SILENT_SOS', 'Silent SOS (Triple Tap)'),
        ('GEOFENCE_AUTOPANIC', 'Auto Geofence Breach Alarm'),
        ('FALL_DETECT', 'Fall / Impact Motion Sensor'),
        ('VOICE_KEYWORD', 'Voice Emergency Keyword'),
    )

    STATUS_CHOICES = (
        ('ACTIVE', 'Active SOS Emergency'),
        ('ACKNOWLEDGED', 'Operator Acknowledged'),
        ('RESPONDING', 'Responders En Route / Responding'),
        ('RESOLVED', 'Resolved & Safe'),
        ('CANCELLED', 'Cancelled by User / False Alarm'),
    )

    sos_id = models.CharField(max_length=32, unique=True, db_index=True)
    tourist = models.ForeignKey('tourists.TouristProfile', on_delete=models.CASCADE, related_name='sos_alerts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    trigger_type = models.CharField(max_length=30, choices=TRIGGER_CHOICES, default='MANUAL_BUTTON')

    latitude = models.FloatField()
    longitude = models.FloatField()
    location_accuracy = models.FloatField(default=5.0)
    battery_level = models.IntegerField(default=100)
    location_address = models.CharField(max_length=255, blank=True)

    emergency_notes = models.TextField(blank=True)
    audio_snapshot = models.FileField(upload_to='sos_audio/', null=True, blank=True)

    triggered_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-triggered_at']

    def save(self, *args, **kwargs):
        if not self.sos_id:
            self.sos_id = f"SOS-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def is_in_progress(self) -> bool:
        return self.status in ['ACTIVE', 'ACKNOWLEDGED', 'RESPONDING']

    def __str__(self):
        return f"{self.sos_id} - {self.tourist.user.username} [{self.get_status_display()}]"


class SOSDispatch(models.Model):
    STATUS_CHOICES = (
        ('ASSIGNED', 'Assigned & Alerted'),
        ('EN_ROUTE', 'En Route to Scene'),
        ('ARRIVED', 'Arrived on Scene'),
        ('COMPLETED', 'Mission Completed'),
    )

    sos = models.ForeignKey(SOSAlert, on_delete=models.CASCADE, related_name='dispatches')
    responder = models.ForeignKey(ResponderUnit, on_delete=models.CASCADE, related_name='dispatches')
    dispatched_at = models.DateTimeField(auto_now_add=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    eta_minutes = models.IntegerField(default=8)
    dispatch_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ASSIGNED')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Dispatch {self.responder.callsign} -> {self.sos.sos_id} [{self.dispatch_status}]"


class SOSLiveBreadcrumb(models.Model):
    sos = models.ForeignKey(SOSAlert, on_delete=models.CASCADE, related_name='breadcrumbs')
    latitude = models.FloatField()
    longitude = models.FloatField()
    speed = models.FloatField(default=0.0)
    battery_level = models.IntegerField(default=100)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['recorded_at']
