from rest_framework import serializers
from .models import ResponderUnit, SOSAlert, SOSDispatch, SOSLiveBreadcrumb


class ResponderUnitSerializer(serializers.ModelSerializer):
    agency_display = serializers.CharField(source='get_agency_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ResponderUnit
        fields = [
            'id', 'unit_code', 'agency', 'agency_display', 'callsign',
            'officer_in_charge', 'contact_number', 'status', 'status_display',
            'current_latitude', 'current_longitude', 'station_base_name', 'last_heartbeat'
        ]


class SOSDispatchSerializer(serializers.ModelSerializer):
    responder = ResponderUnitSerializer(read_only=True)

    class Meta:
        model = SOSDispatch
        fields = ['id', 'responder', 'dispatched_at', 'arrived_at', 'eta_minutes', 'dispatch_status', 'notes']


class SOSLiveBreadcrumbSerializer(serializers.ModelSerializer):
    class Meta:
        model = SOSLiveBreadcrumb
        fields = ['id', 'latitude', 'longitude', 'speed', 'battery_level', 'recorded_at']


class SOSAlertSerializer(serializers.ModelSerializer):
    tourist_name = serializers.CharField(source='tourist.user.get_full_name', read_only=True)
    tourist_phone = serializers.CharField(source='tourist.user.phone_number', read_only=True)
    nationality = serializers.CharField(source='tourist.nationality', read_only=True)
    blood_group = serializers.CharField(source='tourist.blood_group', read_only=True)
    medical_conditions = serializers.CharField(source='tourist.medical_conditions', read_only=True)
    digital_id_number = serializers.SerializerMethodField()
    dispatches = SOSDispatchSerializer(many=True, read_only=True)
    breadcrumbs = SOSLiveBreadcrumbSerializer(many=True, read_only=True)

    def get_digital_id_number(self, obj):
        digital_id = getattr(obj.tourist, 'digital_id', None)
        return digital_id.id_number if digital_id else 'N/A'

    class Meta:
        model = SOSAlert
        fields = [
            'id', 'sos_id', 'tourist', 'tourist_name', 'tourist_phone', 'digital_id_number',
            'nationality', 'blood_group', 'medical_conditions',
            'status', 'trigger_type', 'latitude', 'longitude',
            'location_accuracy', 'battery_level', 'location_address',
            'emergency_notes', 'audio_snapshot', 'triggered_at',
            'acknowledged_at', 'resolved_at', 'cancellation_reason',
            'dispatches', 'breadcrumbs'
        ]
        read_only_fields = ['id', 'sos_id', 'triggered_at']
