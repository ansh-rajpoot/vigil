from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Template Views
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('register/authority/', views.register_authority_view, name='register_authority'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_management_view, name='profile_management'),
    path('admin-portal/', views.admin_portal_view, name='admin_portal'),

    # REST APIs
    path('api/profile/', views.UserProfileAPIView.as_view(), name='api_profile'),
    path('api/emergency-contacts/', views.EmergencyContactsAPIView.as_view(), name='api_emergency_contacts'),
    path('api/admin/users/', views.AdminUserManagementAPIView.as_view(), name='api_admin_users'),
    path('api/admin/users/<int:user_id>/', views.AdminUserManagementAPIView.as_view(), name='api_admin_user_detail'),
]
