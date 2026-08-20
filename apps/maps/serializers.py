from rest_framework import serializers
from .models import SafetyPOI, SafeRoute


class SafetyPOISerializer(serializers.ModelSerializer):
    poi_type_display = serializers.CharField(source='get_poi_type_display', read_only=True)

    class Meta:
        model = SafetyPOI
        fields = [
            'id', 'name', 'poi_type', 'poi_type_display', 'latitude',
            'longitude', 'contact_number', 'is_24_hours', 'address', 'description'
        ]


class SafeRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafeRoute
        fields = '__all__'
