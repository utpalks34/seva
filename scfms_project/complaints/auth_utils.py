import base64
import hashlib
import hmac
import json
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.utils import timezone


ACCESS_TOKEN_LIFETIME = timedelta(hours=8)
REFRESH_TOKEN_LIFETIME = timedelta(days=7)
EMAIL_TOKEN_MAX_AGE = 60 * 60 * 24
ACTIVATION_TOKEN_MAX_AGE = 60 * 60 * 24 * 2
OTP_LIFETIME = timedelta(minutes=10)

signer = TimestampSigner()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _jwt_secret() -> bytes:
    return settings.SECRET_KEY.encode("utf-8")


def create_jwt_pair(user):
    return {
        "access": create_jwt_token(user, token_type="access", lifetime=ACCESS_TOKEN_LIFETIME),
        "refresh": create_jwt_token(user, token_type="refresh", lifetime=REFRESH_TOKEN_LIFETIME),
    }


def create_jwt_token(user, token_type="access", lifetime=ACCESS_TOKEN_LIFETIME):
    now = timezone.now()
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user.pk),
        "email": user.email,
        "role": user.role,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
        "ver": int(getattr(user, "token_version", 0)),
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(_jwt_secret(), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def decode_jwt_token(token: str):
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise ValueError("Malformed token") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(_jwt_secret(), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(signature_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid token signature")

    payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    if int(payload.get("exp", 0)) < int(timezone.now().timestamp()):
        raise ValueError("Token expired")

    return payload


def create_email_verification_token(user):
    return signer.sign(f"verify:{user.pk}:{user.email}")


def read_email_verification_token(token: str):
    value = signer.unsign(token, max_age=EMAIL_TOKEN_MAX_AGE)
    purpose, user_id, email = value.split(":", 2)
    if purpose != "verify":
        raise BadSignature("Invalid verification token")
    return int(user_id), email


def create_activation_token(user):
    return signer.sign(f"activate:{user.pk}:{user.email}")


def read_activation_token(token: str):
    value = signer.unsign(token, max_age=ACTIVATION_TOKEN_MAX_AGE)
    purpose, user_id, email = value.split(":", 2)
    if purpose != "activate":
        raise BadSignature("Invalid activation token")
    return int(user_id), email


def create_otp_code():
    return f"{secrets.randbelow(900000) + 100000}"


def store_otp_on_user(user, otp_code: str):
    user.otp_code_hash = make_password(otp_code)
    user.otp_expires_at = timezone.now() + OTP_LIFETIME
    user.save(update_fields=["otp_code_hash", "otp_expires_at"])


def verify_user_otp(user, otp_code: str) -> bool:
    if not user.otp_code_hash or not user.otp_expires_at:
        return False
    if timezone.now() > user.otp_expires_at:
        return False
    return check_password(otp_code, user.otp_code_hash)


def clear_user_otp(user):
    user.otp_code_hash = ""
    user.otp_expires_at = None
    user.save(update_fields=["otp_code_hash", "otp_expires_at"])


__all__ = [
    "ACTIVATION_TOKEN_MAX_AGE",
    "ACCESS_TOKEN_LIFETIME",
    "BadSignature",
    "EMAIL_TOKEN_MAX_AGE",
    "REFRESH_TOKEN_LIFETIME",
    "SignatureExpired",
    "clear_user_otp",
    "create_activation_token",
    "create_email_verification_token",
    "create_jwt_pair",
    "create_otp_code",
    "decode_jwt_token",
    "read_activation_token",
    "read_email_verification_token",
    "store_otp_on_user",
    "verify_user_otp",
]
