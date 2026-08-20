from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import status

from common.utils import api_response
from .scenario_engine import execute_demo_step, reset_to_demo_baseline
from tourists.models import TouristProfile
from emergency.models import SOSAlert, ResponderUnit
from risk.models import TouristRiskAssessment


def demo_controller_view(request):
    """
    Dedicated SIH Demonstration Director & Control Panel.
    Provides live step triggers, automatic presentation mode,
    side-by-side split view shortcuts, and 1-click baseline resets.
    """
    return render(request, 'demo/controller.html')


class DemoStepAPIView(APIView):
    """Executes a designated step (1 to 12) of the SIH demo flow."""
    permission_classes = [AllowAny]

    def post(self, request, step_id):
        if not (1 <= step_id <= 12):
            return api_response(
                success=False,
                message="Invalid step_id. Please specify an integer between 1 and 12.",
                http_code=status.HTTP_400_BAD_REQUEST
            )
        result = execute_demo_step(step_id)
        return api_response(
            success=True,
            message=f"Step {step_id} executed successfully.",
            data=result,
            http_code=status.HTTP_200_OK
        )


class DemoResetAPIView(APIView):
    """Resets the database state to the pristine SIH demonstration baseline."""
    permission_classes = [AllowAny]

    def post(self, request):
        result = reset_to_demo_baseline()
        return api_response(
            success=True,
            message="Demonstration database reset to baseline state.",
            data=result,
            http_code=status.HTTP_200_OK
        )


class DemoStatusAPIView(APIView):
    """Returns the current runtime state of the demonstration environment."""
    permission_classes = [AllowAny]

    def get(self, request):
        p1 = TouristProfile.objects.filter(user__username='tourist_ananya').first()
        active_sos = SOSAlert.objects.filter(status__in=['ACTIVE', 'ACKNOWLEDGED', 'RESPONDING']).first()
        risk = TouristRiskAssessment.objects.filter(tourist=p1).order_by('-evaluated_at').first() if p1 else None

        state = {
            'tourist_name': 'Ananya Sen',
            'tourist_lat': p1.current_latitude if p1 else None,
            'tourist_lng': p1.current_longitude if p1 else None,
            'tourist_trip_status': p1.trip_status if p1 else None,
            'tourist_risk_score': risk.overall_score if risk else 14,
            'tourist_risk_level': risk.risk_level if risk else 'SAFE',
            'active_sos_id': active_sos.sos_id if active_sos else None,
            'active_sos_status': active_sos.status if active_sos else 'NONE',
            'available_responders': ResponderUnit.objects.filter(status='AVAILABLE').count(),
        }
        return api_response(success=True, data=state)
