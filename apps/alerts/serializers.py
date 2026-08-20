from rest_framework import serializers
from .models import EmergencyBroadcast, AlertReceipt


class EmergencyBroadcastSerializer(serializers.ModelSerializer):
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    target_type_display = serializers.CharField(source='get_target_type_display', read_only=True)
    issued_by_name = serializers.CharField(source='issued_by.get_full_name', read_only=True)
    zone_name = serializers.CharField(source='target_zone.name', read_only=True, default="All Regional Sectors")
    theme = serializers.SerializerMethodField()

    def get_theme(self, obj):
        return obj.get_color_theme()

    class Meta:
        model = EmergencyBroadcast
        fields = [
            'id', 'broadcast_code', 'alert_type', 'alert_type_display',
            'title', 'message', 'severity', 'severity_display',
            'target_type', 'target_type_display',
            'center_latitude', 'center_longitude', 'radius_meters',
            'target_zone', 'zone_name', 'issued_by_name',
            'is_active', 'starts_at', 'expires_at', 'created_at', 'theme'
        ]
        read_only_fields = ['id', 'broadcast_code', 'created_at']


class AlertReceiptSerializer(serializers.ModelSerializer):
    broadcast = EmergencyBroadcastSerializer(read_only=True)

    class Meta:
        model = AlertReceipt
        fields = ['id', 'broadcast', 'delivered_at', 'acknowledged_at']
