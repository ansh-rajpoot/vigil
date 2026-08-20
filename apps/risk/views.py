from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from common.utils import api_response
from .models import Blackspot, TouristRiskAssessment
from .serializers import BlackspotSerializer, TouristRiskAssessmentSerializer
from .engine import get_risk_engine, calculate_tourist_risk
from tourists.models import TouristProfile


class CurrentTouristRiskAPIView(APIView):
    """
    Returns the current tourist's live calculated risk score (0-100),
    category (Safe, Moderate, High, Critical), factor breakdown, and actionable safety guidance.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, 'tourist_profile', None)
        if not profile:
            return api_response(success=False, message="Tourist profile not found", http_code=status.HTTP_404_NOT_FOUND)

        engine = get_risk_engine()
        breakdown = engine.get_factor_breakdown(profile)

        # Retrieve or persist latest evaluation
        assessment = profile.risk_assessments.first()
        if not assessment or (timezone.now() - assessment.evaluated_at).total_seconds() > 60:
            assessment = engine.calculate_risk(profile)

        data = TouristRiskAssessmentSerializer(assessment).data
        data['factors_breakdown'] = breakdown

        return api_response(success=True, message="Current risk score calculated", data=data)


class BlackspotsListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        blackspots = Blackspot.objects.filter(is_active=True)
        return api_response(success=True, message="Active blackspots retrieved", data=BlackspotSerializer(blackspots, many=True).data)


class EvaluateTouristRiskAPIView(APIView):
    """
    Evaluates current risk score for tourist based on given location coordinates, time, zones, and device state.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        tourist_id = request.data.get('tourist_id')

        tourist = None
        if tourist_id:
            tourist = TouristProfile.objects.filter(id=tourist_id).first()
        elif request.user.is_authenticated and hasattr(request.user, 'tourist_profile'):
            tourist = request.user.tourist_profile

        if not tourist:
            return api_response(success=False, message="Tourist profile required for risk evaluation", http_code=status.HTTP_400_BAD_REQUEST)

        if lat is not None and lng is not None:
            lat = float(lat)
            lng = float(lng)

        assessment = calculate_tourist_risk(tourist, current_lat=lat, current_lng=lng)

        return api_response(
            success=True,
            message="Tourist risk evaluated",
            data=TouristRiskAssessmentSerializer(assessment).data
        )


class RiskAnalyticsC2APIView(APIView):
    """Authority C2 analytics endpoint for aggregate risk metrics."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_operator:
            return api_response(success=False, message="Operator authorization required", http_code=status.HTTP_403_FORBIDDEN)

        total_tourists = TouristProfile.objects.count()
        safe_count = TouristRiskAssessment.objects.filter(risk_level='SAFE').count()
        moderate_count = TouristRiskAssessment.objects.filter(risk_level='MODERATE').count()
        high_count = TouristRiskAssessment.objects.filter(risk_level='HIGH').count()
        critical_count = TouristRiskAssessment.objects.filter(risk_level='CRITICAL').count()

        high_risk_tourists = TouristRiskAssessment.objects.filter(risk_level__in=['HIGH', 'CRITICAL']).order_by('-evaluated_at')[:10]

        return api_response(success=True, data={
            'total_monitored_tourists': total_tourists,
            'distribution': {
                'safe': safe_count,
                'moderate': moderate_count,
                'high': high_count,
                'critical': critical_count
            },
            'recent_high_risk_alerts': TouristRiskAssessmentSerializer(high_risk_tourists, many=True).data
        })
