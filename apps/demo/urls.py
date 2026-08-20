from django.urls import path
from . import views

app_name = 'demo'

urlpatterns = [
    path('', views.demo_controller_view, name='controller'),
    path('controller/', views.demo_controller_view, name='controller_alias'),
    path('api/step/<int:step_id>/', views.DemoStepAPIView.as_view(), name='api_step'),
    path('api/reset/', views.DemoResetAPIView.as_view(), name='api_reset'),
    path('api/status/', views.DemoStatusAPIView.as_view(), name='api_status'),
]
