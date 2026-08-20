from rest_framework import serializers
from .models import Blackspot, TouristRiskAssessment


class BlackspotSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Blackspot
        fields = [
            'id', 'name', 'category', 'category_display', 'risk_weight',
            'latitude', 'longitude', 'radius_meters', 'incident_count_30d',
            'safety_advice', 'is_active', 'created_at'
        ]


class TouristRiskAssessmentSerializer(serializers.ModelSerializer):
    tourist_name = serializers.CharField(source='tourist.user.get_full_name', read_only=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)

    class Meta:
        model = TouristRiskAssessment
        fields = [
            'id', 'tourist', 'tourist_name', 'overall_score', 'risk_level',
            'risk_level_display', 'spatial_risk_score', 'temporal_risk_score',
            'isolation_risk_score', 'crowd_risk_score', 'device_health_score',
            'primary_risk_factor', 'ai_recommendation', 'evaluated_at'
        ]
