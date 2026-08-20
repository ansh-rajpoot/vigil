from django.db import models


class SafetyPOI(models.Model):
    POI_TYPE_CHOICES = (
        ('POLICE', 'Police Station / Outpost'),
        ('TOURIST_POLICE', 'Tourist Police Assistance Booth'),
        ('HOSPITAL', 'Hospital / Emergency Care'),
        ('TOURIST_KIOSK', 'Official Tourist Helpdesk & Kiosk'),
        ('SAFE_SHELTER', 'Designated Safe Haven / Shelter'),
        ('EMBASSY', 'Consulate / Foreign Mission'),
        ('BEACH_TOWER', 'Lifeguard Watchtower'),
    )

    name = models.CharField(max_length=150)
    poi_type = models.CharField(max_length=30, choices=POI_TYPE_CHOICES, default='POLICE')
    latitude = models.FloatField()
    longitude = models.FloatField()
    contact_number = models.CharField(max_length=50, blank=True)
    is_24_hours = models.BooleanField(default=True)
    address = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} [{self.get_poi_type_display()}]"


class SafeRoute(models.Model):
    name = models.CharField(max_length=150)
    origin_name = models.CharField(max_length=150)
    destination_name = models.CharField(max_length=150)
    origin_lat = models.FloatField()
    origin_lng = models.FloatField()
    dest_lat = models.FloatField()
    dest_lng = models.FloatField()

    waypoints_geojson = models.JSONField(help_text="Array of [lat, lng] coordinates along the safe corridor")
    safety_score = models.IntegerField(default=90, help_text="Safety Index score (0-100)")
    lighting_rating = models.CharField(max_length=30, default='WELL_LIT', choices=[
        ('WELL_LIT', 'Continuous Street Lighting'),
        ('MODERATE_LIT', 'Partial Lighting'),
        ('POORLY_LIT', 'Dim / Poor Lighting')
    ])
    patrol_frequency = models.CharField(max_length=100, default='Regular Police Patrol (every 15 min)')
    distance_km = models.FloatField(default=2.5)
    estimated_minutes = models.IntegerField(default=25)
    active_safeguards = models.TextField(blank=True, help_text="e.g. CCTV coverage, 2 Police Kiosks, 24x7 Open Stores")
    is_verified = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}: {self.origin_name} -> {self.destination_name} (Safety {self.safety_score}%)"
