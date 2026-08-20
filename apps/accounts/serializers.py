from rest_framework import serializers
from .models import User, EmergencyContact


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ['id', 'name', 'relationship', 'phone_number', 'email', 'is_primary', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'phone_number', 'role', 'badge_number', 'agency_name',
            'is_verified', 'emergency_contacts', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'is_verified']
