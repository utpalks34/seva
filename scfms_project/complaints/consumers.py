# complaints/consumers.py

import json
import urllib.parse

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from .auth_utils import decode_jwt_token

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications and dashboard updates.

    Auth flow:
      1. Try session auth from Django AuthMiddlewareStack
      2. Fall back to JWT passed as '?token=<jwt>' in the query string
    """

    async def connect(self):
        scope_user = self.scope.get("user")
        if scope_user and not scope_user.is_anonymous:
            self.user = scope_user
        else:
            raw_qs = self.scope.get("query_string", b"")
            qs = raw_qs.decode("utf-8") if isinstance(raw_qs, bytes) else raw_qs
            params = urllib.parse.parse_qs(qs)
            token_list = params.get("token", [])
            token_value = token_list[0].strip() if token_list else None
            self.user = await self.get_user_from_jwt(token_value) if token_value else None

        if self.user is None:
            await self.close(code=4003)
            return

        self.user_group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

        if getattr(self.user, "role", None) in {"GO", "AD"}:
            self.go_group_name = "government_officials"
            await self.channel_layer.group_add(self.go_group_name, self.channel_name)
        else:
            self.go_group_name = None

        await self.accept()

    @database_sync_to_async
    def get_user_from_jwt(self, token_key: str):
        try:
            payload = decode_jwt_token(token_key)
            user = User.objects.get(pk=payload["sub"], is_active=True)
            if int(payload.get("ver", -1)) != int(getattr(user, "token_version", 0)):
                return None
            return user
        except Exception:
            return None

    async def disconnect(self, close_code):
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

        if getattr(self, "go_group_name", None):
            await self.channel_layer.group_discard(self.go_group_name, self.channel_name)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            "type": "notification",
            "message": event["message"],
            "timestamp": event.get("timestamp", ""),
            "complaint_id": event.get("complaint_id"),
            "resolution_image_url": event.get("resolution_image_url"),
        }))

    async def broadcast_new_complaint(self, event):
        c = event["complaint_data"]
        await self.send(text_data=json.dumps({
            "type": "new_complaint",
            "id": c["id"],
            "title": c["title"],
            "description": c["description"],
            "category": c["category"],
            "severity_score": float(c["severity_score"]),
            "latitude": float(c["latitude"]),
            "longitude": float(c["longitude"]),
            "image_url": c["image_url"],
            "created_at": c["created_at"],
        }))

    async def broadcast_complaint_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "complaint_update",
            "complaint_id": event["complaint_id"],
            "status": event["status"],
            "timestamp": event.get("timestamp", ""),
        }))

    async def broadcast_dashboard_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "dashboard_update",
            "total_complaints": event["total_complaints"],
            "pending": event["pending"],
            "in_progress": event["in_progress"],
            "resolved": event["resolved"],
            "timestamp": event.get("timestamp", ""),
        }))
