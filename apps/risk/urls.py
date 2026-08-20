from django.urls import path
from . import views

app_name = 'risk'

urlpatterns = [
    path('api/current/', views.CurrentTouristRiskAPIView.as_view(), name='api_current_risk'),
    path('api/evaluate/', views.EvaluateTouristRiskAPIView.as_view(), name='api_evaluate_risk'),
    path('api/blackspots/', views.BlackspotsListAPIView.as_view(), name='api_blackspots'),
    path('api/c2/analytics/', views.RiskAnalyticsC2APIView.as_view(), name='api_c2_analytics'),
]
