from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

from .auth_utils import decode_jwt_token

User = get_user_model()


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Accepts both `Authorization: Bearer <jwt>` and
    `Authorization: Token <jwt>` to stay compatible with the current frontend.
    """

    keyword_aliases = {"bearer", "token"}

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode("utf-8").strip()
        if not header:
            return None

        parts = header.split()
        if len(parts) != 2 or parts[0].lower() not in self.keyword_aliases:
            return None

        raw_token = parts[1]
        try:
            payload = decode_jwt_token(raw_token)
            user = User.objects.get(pk=payload["sub"], is_active=True)
        except User.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("User not found") from exc
        except Exception as exc:
            raise exceptions.AuthenticationFailed(str(exc)) from exc

        if int(payload.get("ver", -1)) != int(getattr(user, "token_version", 0)):
            raise exceptions.AuthenticationFailed("Token has been revoked")

        return user, payload
