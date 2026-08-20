from django.urls import path
from . import views

app_name = 'geofencing'

urlpatterns = [
    # Pages
    path('manage/', views.geofence_manager_view, name='manager'),
    path('geofences/', views.geofence_manager_view, name='geofence_manager'),

    # REST APIs
    path('api/zones/', views.GeoZoneListCreateAPIView.as_view(), name='api_zones'),
    path('api/zones/<int:zone_id>/', views.GeoZoneDetailAPIView.as_view(), name='api_zone_detail'),
    path('api/check-containment/', views.CheckLocationContainmentAPIView.as_view(), name='api_check_containment'),
    path('api/breaches/<int:breach_id>/acknowledge/', views.AcknowledgeBreachAPIView.as_view(), name='api_acknowledge_breach'),
]
