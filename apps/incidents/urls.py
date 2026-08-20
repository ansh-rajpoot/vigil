from django.urls import path
from . import views

app_name = 'incidents'

urlpatterns = [
    # Public & Tourist Incident Views
    path('', views.incidents_public_feed_view, name='incident_feed'),
    path('feed/', views.incidents_public_feed_view, name='incident_feed_alias'),
    path('report/', views.tourist_report_view, name='tourist_report'),
    path('detail/<str:incident_id>/', views.incident_detail_view, name='incident_detail'),

    # Authority C2 Triage
    path('c2/', views.incidents_c2_view, name='c2_list'),

    # REST APIs
    path('api/', views.IncidentListCreateAPIView.as_view(), name='api_incidents'),
    path('api/list/', views.IncidentListCreateAPIView.as_view(), name='api_incidents_list'),
    path('api/<str:incident_id>/', views.IncidentDetailUpdateAPIView.as_view(), name='api_incident_detail'),
]
