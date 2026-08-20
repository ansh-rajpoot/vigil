from rest_framework import serializers
from .models import TouristProfile, TouristLocationHistory
from accounts.serializers import UserSerializer, EmergencyContactSerializer


class TouristLocationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TouristLocationHistory
        fields = ['id', 'latitude', 'longitude', 'speed', 'battery_level', 'accuracy', 'timestamp']


class TouristProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    is_sos = serializers.BooleanField(read_only=True)

    class Meta:
        model = TouristProfile
        fields = [
            'id', 'user', 'nationality', 'id_document_type', 'blood_group',
            'medical_conditions', 'allergies', 'hotel_stay_details',
            'destination_city', 'trip_start_date', 'trip_end_date',
            'trip_status', 'is_sos', 'current_latitude', 'current_longitude',
            'last_location_time', 'battery_level', 'is_live_tracking_enabled',
            'last_safe_checkin', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
