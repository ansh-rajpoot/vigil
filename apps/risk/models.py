from django.db import models
from django.utils import timezone


class Blackspot(models.Model):
    CATEGORY_CHOICES = (
        ('THEFT_PRONE', 'High Theft / Snatching Zone'),
        ('ISOLATED_UNLIT', 'Isolated / Unlit Night Stretch'),
        ('ACCIDENT_PRONE', 'Accident & Collision Blackspot'),
        ('WATER_HAZARD', 'Dangerous Waters / Rip Current Zone'),
        ('SCAM_CONCENTRATION', 'Tourist Scam / Tout Concentration'),
        ('RUGGED_CLIFF', 'Treacherous Cliff / Slip Hazard'),
    )

    name = models.CharField(max_length=150)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    risk_weight = models.IntegerField(default=75, help_text="Risk factor severity (1-100)")
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius_meters = models.IntegerField(default=300)
    incident_count_30d = models.IntegerField(default=8)
    safety_advice = models.TextField(help_text="Actionable advice for tourists venturing nearby")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_category_display()}) - Weight {self.risk_weight}"


class TouristRiskAssessment(models.Model):
    RISK_LEVEL_CHOICES = (
        ('SAFE', 'Safe (0–30)'),
        ('MODERATE', 'Moderate (31–60)'),
        ('HIGH', 'High (61–80)'),
        ('CRITICAL', 'Critical (81–100)'),
    )

    tourist = models.ForeignKey('tourists.TouristProfile', on_delete=models.CASCADE, related_name='risk_assessments')
    overall_score = models.IntegerField(default=15, help_text="Overall composite risk index (0-100)")
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default='SAFE')

    # Sub-indices
    spatial_risk_score = models.IntegerField(default=10, help_text="Proximity to blackspots and high risk zones (0-35)")
    temporal_risk_score = models.IntegerField(default=10, help_text="Late night / isolated hours factor (0-25)")
    isolation_risk_score = models.IntegerField(default=10, help_text="Distance from police booths and safe havens (0-20)")
    crowd_risk_score = models.IntegerField(default=10, help_text="Disaster alerts & geofences (0-15)")
    device_health_score = models.IntegerField(default=5, help_text="Battery depletion risk (0-10)")

    primary_risk_factor = models.CharField(max_length=255, blank=True)
    ai_recommendation = models.TextField(blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-evaluated_at']

    def get_risk_badge_class(self):
        if self.risk_level == 'SAFE':
            return 'badge-safe'
        elif self.risk_level == 'MODERATE':
            return 'badge-warning'
        elif self.risk_level == 'HIGH':
            return 'badge-high-risk'
        return 'badge-critical'

    def __str__(self):
        return f"{self.tourist.user.username} Risk Score: {self.overall_score}/100 [{self.risk_level}]"
