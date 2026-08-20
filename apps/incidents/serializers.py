from rest_framework import serializers
from .models import Incident, IncidentTimeline


class IncidentTimelineSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True)

    class Meta:
        model = IncidentTimeline
        fields = ['id', 'status', 'note', 'actor_name', 'timestamp']


class IncidentSerializer(serializers.ModelSerializer):
    timeline = IncidentTimelineSerializer(many=True, read_only=True)
    responder_callsign = serializers.CharField(source='assigned_responder.callsign', read_only=True)

    class Meta:
        model = Incident
        fields = [
            'id', 'incident_id', 'reporter', 'reporter_name', 'reporter_phone',
            'category', 'severity', 'status', 'title', 'description',
            'latitude', 'longitude', 'location_name', 'evidence_image',
            'assigned_responder', 'responder_callsign', 'timeline',
            'created_at', 'updated_at', 'resolved_at', 'resolution_notes'
        ]
        read_only_fields = ['id', 'incident_id', 'created_at', 'updated_at']
