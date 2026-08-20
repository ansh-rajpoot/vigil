from django.urls import path, re_path
from emergency.consumers import C2OperationsConsumer, SOSBeaconConsumer, TouristAlertConsumer

websocket_urlpatterns = [
    path('ws/c2/telemetry/', C2OperationsConsumer.as_asgi()),
    path('ws/c2/stream/', C2OperationsConsumer.as_asgi()),
    path('ws/sos/<str:sos_id>/', SOSBeaconConsumer.as_asgi()),
    path('ws/tourist/alerts/<int:user_id>/', TouristAlertConsumer.as_asgi()),
    path('ws/tourist/alerts/', TouristAlertConsumer.as_asgi()),
]
