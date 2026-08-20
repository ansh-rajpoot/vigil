from rest_framework import serializers
from .models import VisionCameraFeed, VisionDetectionLog


class VisionDetectionLogSerializer(serializers.ModelSerializer):
    camera_code = serializers.CharField(source='camera.camera_code', read_only=True)
    location_name = serializers.CharField(source='camera.location_name', read_only=True)
    zone_name = serializers.CharField(source='camera.zone.name', read_only=True, default="General Sector")
    density_tier_display = serializers.CharField(source='get_density_tier_display', read_only=True)
    anomaly_display = serializers.CharField(source='get_anomaly_detected_display', read_only=True)

    class Meta:
        model = VisionDetectionLog
        fields = [
            'id', 'camera', 'camera_code', 'location_name', 'zone_name', 'timestamp',
            'crowd_count', 'crowd_density_score', 'density_tier', 'density_tier_display',
            'people_per_sqm', 'surge_rate_per_min', 'concentration_index',
            'anomaly_detected', 'anomaly_display', 'confidence_score',
            'annotated_frame', 'alert_dispatched', 'notes'
        ]


class VisionCameraFeedSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source='zone.name', read_only=True, default="General Sector")
    latest_detection = serializers.SerializerMethodField()

    class Meta:
        model = VisionCameraFeed
        fields = [
            'id', 'camera_code', 'location_name', 'zone', 'zone_name', 'latitude', 'longitude',
            'stream_url', 'is_active', 'max_safe_capacity', 'critical_threshold_count',
            'surge_threshold_rate', 'coverage_area_sqm', 'sample_frame',
            'last_processed_at', 'latest_detection'
        ]

    def get_latest_detection(self, obj):
        latest = obj.detections.order_by('-timestamp').first()
        return VisionDetectionLogSerializer(latest).data if latest else None
