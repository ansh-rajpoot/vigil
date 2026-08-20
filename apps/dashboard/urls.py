from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('c2/', views.c2_command_view, name='c2_command'),
    path('analytics/', views.analytics_dashboard_view, name='analytics_dashboard'),
    path('api/telemetry/', views.C2TelemetryAPIView.as_view(), name='api_telemetry_alias'),
    path('api/c2/telemetry/', views.C2TelemetryAPIView.as_view(), name='api_c2_telemetry'),
    path('api/c2/charts/', views.C2ChartsAPIView.as_view(), name='api_c2_charts'),
    path('api/analytics/', views.C2ChartsAPIView.as_view(), name='api_analytics'),
]
