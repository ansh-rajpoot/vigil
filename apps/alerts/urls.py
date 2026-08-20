from django.urls import path
from . import views

app_name = 'alerts'

urlpatterns = [
    path('broadcasts/', views.broadcast_c2_view, name='broadcast_c2'),
    path('api/', views.BroadcastListCreateAPIView.as_view(), name='api_broadcasts'),
    path('api/<str:broadcast_code>/acknowledge/', views.AcknowledgeAlertAPIView.as_view(), name='api_acknowledge_alert'),
]
