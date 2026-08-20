from django.urls import path
from . import views

app_name = 'emergency'

urlpatterns = [
    # Pages
    path('fleet/', views.fleet_manager_view, name='fleet_manager'),
    path('active/<str:sos_id>/', views.sos_active_view, name='sos_active'),

    # Responder Fleet Management & Live GPS Telemetry APIs
    path('api/fleet/', views.ResponderFleetListCreateAPIView.as_view(), name='api_fleet_alias'),
    path('api/responders/', views.ResponderFleetListCreateAPIView.as_view(), name='api_responders'),
    path('api/responders/<int:unit_id>/', views.ResponderDetailUpdateAPIView.as_view(), name='api_responder_detail'),
    path('api/responders/<int:unit_id>/location/', views.ResponderLiveLocationAPIView.as_view(), name='api_responder_location'),
    path('api/responders/<int:unit_id>/telemetry/', views.ResponderLiveLocationAPIView.as_view(), name='api_responder_telemetry'),

    # SOS Alert APIs
    path('api/trigger/', views.TriggerSOSAPIView.as_view(), name='api_trigger_sos'),
    path('api/sos/trigger/', views.TriggerSOSAPIView.as_view(), name='api_sos_trigger_alias'),
    path('api/<str:sos_id>/acknowledge/', views.AcknowledgeSOSAPIView.as_view(), name='api_acknowledge_sos'),
    path('api/<str:sos_id>/respond/', views.RespondSOSAPIView.as_view(), name='api_respond_sos'),
    path('api/<str:sos_id>/dispatch/', views.RespondSOSAPIView.as_view(), name='api_dispatch_responder'),
    path('api/<str:sos_id>/on-scene/', views.MarkOnSceneSOSAPIView.as_view(), name='api_on_scene_sos'),
    path('api/<str:sos_id>/resolve/', views.ResolveSOSAPIView.as_view(), name='api_resolve_sos'),
    path('api/<str:sos_id>/cancel/', views.CancelSOSAPIView.as_view(), name='api_cancel_sos'),
    path('api/sos/<str:sos_id>/cancel/', views.CancelSOSAPIView.as_view(), name='api_sos_cancel_alias'),
    path('api/active/', views.ActiveSOSListAPIView.as_view(), name='api_active_sos'),
]
