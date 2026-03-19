# complaints/consumers.py

import json
import urllib.parse
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications and updates.

    Auth flow:
      1. Try session-based auth from Django AuthMiddlewareStack (scope['user'])
      2. Fall back to DRF token passed as '?token=<key>' query parameter
    """

    async def connect(self):
        # ── 1. Try session / cookie auth first ───────────────────────
        scope_user = self.scope.get("user")
        if scope_user and not scope_user.is_anonymous:
            self.user = scope_user
            print(f"✅ WS auth via session: {self.user}")
        else:
            # ── 2. Fall back to token in query string ─────────────────
            raw_qs = self.scope.get("query_string", b"")
            qs = raw_qs.decode("utf-8") if isinstance(raw_qs, bytes) else raw_qs
            params = urllib.parse.parse_qs(qs)          # safe URL-decode
            token_list = params.get("token", [])
            token_value = token_list[0].strip() if token_list else None

            print(f"🔍 WS query string: '{qs}'")
            print(f"🔍 Extracted token: '{token_value[:20] if token_value else None}…'")

            if token_value:
                self.user = await self.get_user_from_token(token_value)
                print(f"🔍 Token DB lookup result: {self.user}")
            else:
                self.user = None
                print("❌ No token in query string")

        # ── Reject if still unauthenticated ──────────────────────────
        if self.user is None:
            print("❌ WebSocket rejected: token not found in DB")
            await self.close(code=4003)
            return

        # ── Join user-specific group ──────────────────────────────────
        self.user_group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

        # ── Join GO broadcast group if applicable ─────────────────────
        if getattr(self.user, "role", None) == "GO":
            self.go_group_name = "government_officials"
            await self.channel_layer.group_add(self.go_group_name, self.channel_name)
        else:
            self.go_group_name = None

        await self.accept()
        print(f"✅ WS connected – user {self.user.id} role={getattr(self.user,'role','PC')}")

    # ── DB helper (runs in thread pool) ──────────────────────────────
    @database_sync_to_async
    def get_user_from_token(self, token_key: str):
        """
        Look up a DRF Token and return the related User, or None.
        """
        try:
            token = Token.objects.select_related("user").get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            print(f"❌ Token not found in DB: '{token_key[:20]}…'")
            return None
        except Exception as exc:
            print(f"❌ Token lookup error: {exc}")
            return None

    # ── Disconnect ────────────────────────────────────────────────────
    async def disconnect(self, close_code):
        user_id = getattr(self.user, "id", "unknown") if self.user else "unknown"

        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

        if getattr(self, "go_group_name", None):
            await self.channel_layer.group_discard(self.go_group_name, self.channel_name)

        print(f"🔌 WS disconnected – user {user_id} code={close_code}")

    # ── Message handlers ──────────────────────────────────────────────

    async def send_notification(self, event):
        """User-specific notification (complaint status change)."""
        await self.send(text_data=json.dumps({
            "type": "notification",
            "message": event["message"],
            "timestamp": event.get("timestamp", ""),
        }))

    async def broadcast_new_complaint(self, event):
        """New complaint broadcast → all GO clients."""
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
        """Complaint status changed → all GO clients."""
        await self.send(text_data=json.dumps({
            "type": "complaint_update",
            "complaint_id": event["complaint_id"],
            "status": event["status"],
            "timestamp": event.get("timestamp", ""),
        }))

    async def broadcast_dashboard_update(self, event):
        """Real-time dashboard metric refresh → all GO clients."""
        await self.send(text_data=json.dumps({
            "type": "dashboard_update",
            "total_complaints": event["total_complaints"],
            "pending": event["pending"],
            "in_progress": event["in_progress"],
            "resolved": event["resolved"],
            "timestamp": event.get("timestamp", ""),
        }))