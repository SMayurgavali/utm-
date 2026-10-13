import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict, Optional

from backend.config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 200_000
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.strip().encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            algorithm, iterations, salt, digest = stored_hash.split("$")
            if algorithm != "pbkdf2_sha256":
                return False
            derived = hashlib.pbkdf2_hmac(
                "sha256",
                password.strip().encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            )
            return hmac.compare_digest(derived.hex(), digest)
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(
        hashlib.sha256(password.strip().encode("utf-8")).hexdigest(),
        stored_hash,
    )


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def issue_session_token(subject: str, role: str) -> str:
    now = int(time.time())
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + settings.session_ttl_seconds,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    token = _b64encode(payload_json)
    signature = hmac.new(settings.secret_key.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{token}.{signature}"


def verify_session_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    try:
        encoded_payload, signature = token.split(".", 1)
        expected = hmac.new(settings.secret_key.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_b64decode(encoded_payload).decode("utf-8"))
        if int(payload.get("exp", 0)) < time.time():
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
