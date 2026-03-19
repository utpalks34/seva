# scfms_backend/asgi.py

import os
import sys
import django
from pathlib import Path

# Add the project directory to the Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scfms_backend.settings')
django.setup()

from complaints import routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    # WebSocket communication will be handled by AuthMiddlewareStack and URLRouter
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})