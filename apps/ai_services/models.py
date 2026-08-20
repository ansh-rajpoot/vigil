from django.db import models


class VisionCameraFeed(models.Model):
    camera_code = models.CharField(max_length=50, unique=True, db_index=True)
    location_name = models.CharField(max_length=150)
    zone = models.ForeignKey('geofencing.GeoZone', null=True, blank=True, on_delete=models.SET_NULL, related_name='camera_feeds', help_text="Associated geographic safety zone")
    latitude = models.FloatField()
    longitude = models.FloatField()
    stream_url = models.CharField(max_length=255, blank=True, help_text="RTSP or live video stream URL")
    is_active = models.BooleanField(default=True)

    # Operational Capacity & Thresholds
    max_safe_capacity = models.IntegerField(default=120, help_text="Maximum safe tourist capacity in this camera sector")
    critical_threshold_count = models.IntegerField(default=100, help_text="Threshold count that triggers automated congestion alert")
    surge_threshold_rate = models.IntegerField(default=25, help_text="Rate of increase (people/min) that triggers surge alarm")
    coverage_area_sqm = models.FloatField(default=250.0, help_text="Camera field-of-view physical coverage area in square meters")

    sample_frame = models.ImageField(upload_to='cctv_samples/', null=True, blank=True)
    last_processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        zone_str = f" [{self.zone.name}]" if self.zone else ""
        return f"{self.camera_code} - {self.location_name}{zone_str}"


class VisionDetectionLog(models.Model):
    DENSITY_TIERS = (
        ('LOW', 'Low Density (Safe)'),
        ('NORMAL', 'Optimal Density'),
        ('HIGH', 'High Density (Advisory)'),
        ('CRITICAL_SURGE', 'Critical Surge / Stampede Hazard'),
    )

    ANOMALY_CHOICES = (
        ('NONE', 'Normal Flow'),
        ('CROWD_SURGE', 'Sudden Crowd Surge / Influx'),
        ('ABNORMAL_CONCENTRATION', 'Abnormal Spatial Concentration / Bottleneck'),
        ('OVERCROWDING', 'Severe Capacity Exceeded'),
    )

    camera = models.ForeignKey(VisionCameraFeed, on_delete=models.CASCADE, related_name='detections')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Estimated Metrics
    crowd_count = models.IntegerField(default=0)
    crowd_density_score = models.FloatField(default=0.0, help_text="Normalized 0-100 crowd density index")
    density_tier = models.CharField(max_length=20, choices=DENSITY_TIERS, default='NORMAL')
    people_per_sqm = models.FloatField(default=0.0, help_text="Estimated people density per square meter")
    surge_rate_per_min = models.FloatField(default=0.0, help_text="Crowd rate of change in people per minute")
    concentration_index = models.FloatField(default=0.0, help_text="Spatial bottleneck concentration index (0.0 - 1.0)")

    anomaly_detected = models.CharField(max_length=30, choices=ANOMALY_CHOICES, default='NONE')
    confidence_score = models.FloatField(default=0.92)
    annotated_frame = models.ImageField(upload_to='ai_frames/', null=True, blank=True)
    alert_dispatched = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def is_threshold_exceeded(self) -> bool:
        return self.crowd_density_score >= 75.0 or self.anomaly_detected != 'NONE' or self.crowd_count >= self.camera.critical_threshold_count

    def __str__(self):
        return f"{self.camera.camera_code} @ {self.timestamp:%H:%M:%S}: {self.crowd_count} ppl (Score: {self.crowd_density_score:.0f}/100) [{self.density_tier}] Anomaly: {self.anomaly_detected}"
