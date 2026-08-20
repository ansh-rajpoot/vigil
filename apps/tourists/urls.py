from django.urls import path
from . import views

app_name = 'tourists'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('profile/', views.profile_view, name='profile'),

    # REST APIs
    path('api/location/', views.UpdateLocationAPIView.as_view(), name='api_location'),
    path('api/update-location/', views.UpdateLocationAPIView.as_view(), name='api_update_location'),
    path('api/checkin/', views.SafeCheckinAPIView.as_view(), name='api_safe_checkin'),
]
