from rest_framework import serializers
from .models import GeoZone, GeofenceBreachLog


class GeoZoneSerializer(serializers.ModelSerializer):
    is_curfew_active = serializers.BooleanField(source='is_curfew_active_now', read_only=True)

    class Meta:
        model = GeoZone
        fields = [
            'id', 'name', 'code', 'zone_type', 'description', 'polygon_geojson',
            'center_latitude', 'center_longitude', 'radius_meters', 'is_active',
            'curfew_start_time', 'curfew_end_time', 'is_curfew_active',
            'max_crowd_threshold', 'safety_advisory', 'created_at'
        ]


class GeofenceBreachLogSerializer(serializers.ModelSerializer):
    tourist_name = serializers.CharField(source='tourist.user.get_full_name', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    zone_type = serializers.CharField(source='zone.zone_type', read_only=True)

    class Meta:
        model = GeofenceBreachLog
        fields = [
            'id', 'tourist', 'tourist_name', 'zone', 'zone_name', 'zone_type',
            'breach_type', 'latitude', 'longitude', 'timestamp',
            'is_acknowledged', 'action_taken', 'resolved_at'
        ]
