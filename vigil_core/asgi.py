"""
ASGI config for vigil_core project.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vigil_core.settings')
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import vigil_core.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            vigil_core.routing.websocket_urlpatterns
        )
    ),
})
