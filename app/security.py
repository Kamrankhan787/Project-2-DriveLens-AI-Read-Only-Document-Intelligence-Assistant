"""
DriveLens AI - Security, Session Handling, and CSRF Protection
"""
import secrets
import logging
from typing import Optional, Dict, Any
from itsdangerous import URLSafeTimedSerializer, URLSafeSerializer, BadSignature, SignatureExpired
from app.config import settings

logger = logging.getLogger("drivelens.security")

# State serializer has expiration (e.g., 10 minutes)
_state_serializer = URLSafeTimedSerializer(settings.SESSION_SECRET_KEY, salt="drivelens-oauth-state")

# Session serializer signs session payloads stored in HTTP-only cookies
_session_serializer = URLSafeSerializer(settings.SESSION_SECRET_KEY, salt="drivelens-session-cookie")


def generate_oauth_state() -> str:
    """
    Generates a cryptographically secure, signed OAuth state token to protect against CSRF.
    Contains high-entropy random hex plus a cryptographic signature.
    """
    nonce = secrets.token_hex(16)
    return _state_serializer.dumps({"nonce": nonce})


def verify_oauth_state(state: str, max_age_seconds: int = 600) -> bool:
    """
    Validates the OAuth state token and checks if it was signed by this server
    and not expired (default 10 minutes).
    """
    if not state:
        return False
    try:
        data = _state_serializer.loads(state, max_age=max_age_seconds)
        return isinstance(data, dict) and "nonce" in data
    except (SignatureExpired, BadSignature) as e:
        logger.warning(f"Invalid or expired OAuth state token: {type(e).__name__}")
        return False


def serialize_session(data: Dict[str, Any]) -> str:
    """
    Serializes and cryptographically signs user session data for storage in an HTTP-only cookie.
    """
    return _session_serializer.dumps(data)


def deserialize_session(cookie_value: str) -> Optional[Dict[str, Any]]:
    """
    Verifies signature and deserializes session cookie data.
    Returns None if signature is invalid or tampered with.
    """
    if not cookie_value:
        return None
    try:
        data = _session_serializer.loads(cookie_value)
        if isinstance(data, dict):
            return data
        return None
    except BadSignature:
        logger.warning("Tampered or invalid session cookie detected.")
        return None


def mask_secret(secret: Optional[str]) -> str:
    """
    Masks API keys, tokens, and secrets so they are never exposed in logs or UI.
    """
    if not secret:
        return ""
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"


def verify_strictly_readonly_scope(scope_string: str) -> bool:
    """
    Ensures that the OAuth scope granted or requested contains NO write capabilities.
    """
    forbidden = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.appdata",
        "https://www.googleapis.com/auth/drive.scripts",
    ]
    scopes = scope_string.split()
    for s in scopes:
        if s in forbidden:
            return False
    return True
