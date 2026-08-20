from django.db import models
from django.conf import settings
from django.utils import timezone


class TouristProfile(models.Model):
    TRIP_STATUS_CHOICES = (
        ('PLANNING', 'Planning'),
        ('ACTIVE', 'Active Trip'),
        ('COMPLETED', 'Completed'),
        ('SOS_ACTIVE', 'SOS Emergency Active'),
    )

    BLOOD_GROUPS = (
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tourist_profile')
    nationality = models.CharField(max_length=100, default='Indian')
    id_document_type = models.CharField(max_length=50, default='Aadhaar', help_text="e.g. Passport, Aadhaar, National ID")
    id_document_hash = models.CharField(max_length=128, blank=True, help_text="SHA-256 hash of document for privacy verification")
    blood_group = models.CharField(max_length=10, blank=True, choices=BLOOD_GROUPS)
    medical_conditions = models.TextField(blank=True, help_text="Pre-existing conditions, cardiac history, etc.")
    allergies = models.TextField(blank=True, help_text="Medication/food allergies")
    hotel_stay_details = models.CharField(max_length=255, blank=True)
    destination_city = models.CharField(max_length=100, default='Goa, India')

    trip_start_date = models.DateField(null=True, blank=True)
    trip_end_date = models.DateField(null=True, blank=True)
    trip_status = models.CharField(max_length=20, choices=TRIP_STATUS_CHOICES, default='ACTIVE')

    current_latitude = models.FloatField(null=True, blank=True)
    current_longitude = models.FloatField(null=True, blank=True)
    last_location_time = models.DateTimeField(null=True, blank=True)
    battery_level = models.IntegerField(default=95, help_text="Battery percentage (0-100)")
    is_live_tracking_enabled = models.BooleanField(default=True)

    safe_checkin_interval_mins = models.IntegerField(default=120)
    last_safe_checkin = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.destination_city})"

    @property
    def is_sos(self):
        return self.trip_status == 'SOS_ACTIVE'


class TouristLocationHistory(models.Model):
    tourist = models.ForeignKey(TouristProfile, on_delete=models.CASCADE, related_name='location_history')
    latitude = models.FloatField()
    longitude = models.FloatField()
    speed = models.FloatField(default=0.0, help_text="Speed in km/h")
    battery_level = models.IntegerField(default=100)
    accuracy = models.FloatField(default=5.0, help_text="GPS accuracy in meters")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.tourist.user.username} @ ({self.latitude:.4f}, {self.longitude:.4f}) - {self.timestamp:%H:%M:%S}"
