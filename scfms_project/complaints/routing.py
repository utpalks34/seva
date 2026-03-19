# complaints/routing.py

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # The URL the frontend will connect to
    re_path(r'^ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]