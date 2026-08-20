import os
import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_incident_media(file):
    """
    Validates uploaded incident evidence:
    - Maximum file size: 15 MB
    - Permitted extensions: jpg, jpeg, png, webp, mp4, mov, avi
    """
    max_size_mb = 15
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Maximum upload file size is {max_size_mb} MB.")

    ext = os.path.splitext(file.name)[1].lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov', '.avi']
    if ext not in allowed_extensions:
        raise ValidationError(f"Unsupported file format '{ext}'. Allowed formats: {', '.join(allowed_extensions)}")


class Incident(models.Model):
    CATEGORY_CHOICES = (
        ('ACCIDENT', 'Accident / Collision'),
        ('CRIME', 'Crime / Theft / Assault'),
        ('HARASSMENT', 'Harassment / Eve Teasing'),
        ('MEDICAL', 'Medical Emergency'),
        ('LOST_PERSON', 'Lost Tourist / Missing Person'),
        ('LOST_PROPERTY', 'Lost Property / Valuables'),
        ('NATURAL_DISASTER', 'Natural Disaster / Flood / Landslide'),
        ('UNSAFE_AREA', 'Unsafe Area / Broken Streetlights / Hazard'),
        ('OTHER', 'Other / General Incident'),
    )

    SEVERITY_CHOICES = (
        ('LOW', 'Low Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('HIGH', 'High Priority'),
        ('CRITICAL', 'Critical / Life Threatening'),
    )

    STATUS_CHOICES = (
        ('REPORTED', 'Reported / Pending Review'),
        ('VERIFIED', 'Verified / Triage Complete'),
        ('ASSIGNED', 'Assigned to Responder Unit'),
        ('IN_PROGRESS', 'Investigation / Response In Progress'),
        ('RESOLVED', 'Resolved & Closed'),
        ('REJECTED', 'Rejected / False Alarm'),
    )

    incident_id = models.CharField(max_length=32, unique=True, db_index=True)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reported_incidents')
    reporter_name = models.CharField(max_length=150, blank=True)
    reporter_phone = models.CharField(max_length=50, blank=True)

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='OTHER')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REPORTED')

    title = models.CharField(max_length=200)
    description = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    location_name = models.CharField(max_length=255, blank=True, help_text="e.g. Baga Beach Shack #4, Panaji Promenade")

    evidence_image = models.FileField(upload_to='incidents/', null=True, blank=True, validators=[validate_incident_media])
    assigned_responder = models.ForeignKey('emergency.ResponderUnit', null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_incidents')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.incident_id:
            self.incident_id = f"INC-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.incident_id} [{self.get_severity_display()}] - {self.title}"


class IncidentTimeline(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='timeline')
    status = models.CharField(max_length=30)
    note = models.TextField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.incident.incident_id} -> {self.status} at {self.timestamp:%H:%M}"
