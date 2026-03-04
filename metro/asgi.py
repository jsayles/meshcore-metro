import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from django.urls import path


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "metro.settings")


# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import after Django initialization to avoid AppRegistryNotReady errors
from metro.consumers import MonitoringConsumer  # noqa: E402


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                [
                    path("ws/monitoring/", MonitoringConsumer.as_asgi()),
                ]
            )
        ),
    }
)
