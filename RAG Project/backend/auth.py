import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from .config import ACCESS_TOKEN_EXPIRE_HOURS, AUTH_SECRET


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    )
    return f"{salt}${base64.urlsafe_b64encode(digest).decode('utf-8')}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, _ = stored_hash.split("$", 1)
    except ValueError:
        return False

    expected = hash_password(password, salt)
    return hmac.compare_digest(expected, stored_hash)


def create_access_token(user_id: int, email: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": int(expires_at.timestamp()),
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")
    signature = hmac.new(AUTH_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def decode_access_token(token: str) -> dict:
    try:
        body, signature = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("Invalid token format.") from exc

    expected_signature = hmac.new(
        AUTH_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Invalid token signature.")

    padding = "=" * (-len(body) % 4)
    payload = json.loads(base64.urlsafe_b64decode(body + padding).decode("utf-8"))
    if int(payload["exp"]) < int(datetime.now(UTC).timestamp()):
        raise ValueError("Token expired.")

    return payload
