from rest_framework import serializers
from .models import DigitalTouristID, IDVerificationLog


class IDVerificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = IDVerificationLog
        fields = '__all__'


class DigitalTouristIDSerializer(serializers.ModelSerializer):
    tourist_name = serializers.CharField(source='tourist.user.get_full_name', read_only=True)
    nationality = serializers.CharField(source='tourist.nationality', read_only=True)
    blood_group = serializers.CharField(source='tourist.blood_group', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    qr_payload = serializers.SerializerMethodField()

    class Meta:
        model = DigitalTouristID
        fields = [
            'id', 'id_number', 'tourist_name', 'nationality', 'blood_group',
            'status', 'is_valid', 'issued_at', 'valid_until', 'qr_code_image',
            'qr_payload'
        ]

    def get_qr_payload(self, obj):
        return obj.get_qr_payload_dict()
