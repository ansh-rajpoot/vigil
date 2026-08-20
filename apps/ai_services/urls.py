from django.urls import path
from . import views

app_name = 'ai_services'

urlpatterns = [
    path('c2/', views.crowd_ai_c2_view, name='crowd_ai_c2'),
    # API endpoints
    path('api/feeds/', views.CameraFeedsListAPIView.as_view(), name='api_camera_feeds'),
    path('api/analyze-frame/', views.AnalyzeImageFrameAPIView.as_view(), name='api_analyze_frame'),
]
