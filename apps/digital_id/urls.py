from django.urls import path
from . import views

app_name = 'digital_id'

urlpatterns = [
    # Pages
    path('card/', views.tourist_id_card_view, name='tourist_id_card'),
    path('verify/', views.public_verify_portal_view, name='verify_portal'),

    # REST APIs
    path('api/dynamic-qr/', views.DynamicQRTokenAPIView.as_view(), name='api_dynamic_qr'),
    path('api/verify/', views.VerifyTouristIDAPIView.as_view(), name='api_verify_id'),
    path('api/logs/', views.DigitalIDLogsAPIView.as_view(), name='api_logs'),
]
