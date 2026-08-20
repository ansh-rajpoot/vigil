"""
URL configuration for vigil_core project.
"""
from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.shortcuts import render, redirect

def root_redirect(request):
    if request.user.is_authenticated:
        if getattr(request.user, 'is_tourism_admin', False):
            return redirect('accounts:admin_portal')
        elif getattr(request.user, 'is_authority', False):
            return redirect('dashboard:c2_command')
        return redirect('tourists:home')
    return redirect('accounts:login')

def design_system_view(request):
    return render(request, 'design_system_preview.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', root_redirect, name='root_redirect'),
    path('design-system/', design_system_view, name='design_system'),
    path('auth/', include('accounts.urls', namespace='accounts')),
    path('tourist/', include('tourists.urls', namespace='tourists')),
    path('digital-id/', include('digital_id.urls', namespace='digital_id')),
    path('geofencing/', include('geofencing.urls', namespace='geofencing')),
    path('incidents/', include('incidents.urls', namespace='incidents')),
    path('emergency/', include('emergency.urls', namespace='emergency')),
    path('risk/', include('risk.urls', namespace='risk')),
    path('maps/', include('maps.urls', namespace='maps')),
    path('alerts/', include('alerts.urls', namespace='alerts')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('ai-services/', include('ai_services.urls', namespace='ai_services')),
    path('demo/', include('demo.urls', namespace='demo')),

    # Media files serving (avatars, evidence uploads, QR codes)
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
