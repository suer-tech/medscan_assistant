"""Single-owner authentication configured by the deployment, never by source code."""
import hashlib
import os
from datetime import datetime, timezone
from typing import Optional

from passlib.context import CryptContext
from passlib.exc import MissingBackendError

from server._core.const import ONE_YEAR_MS


_password_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt"],
    pbkdf2_sha256__default_rounds=600_000,
    deprecated="auto",
)
_created_at = datetime.now(timezone.utc)
_last_signed_in: dict[str, datetime] = {}


def _admin_credentials() -> Optional[tuple[str, str]]:
    """Return configured credentials, or disable login for missing/invalid settings."""
    email = os.getenv("MEDSCAN_ADMIN_EMAIL", "").strip().lower()
    password_hash = os.getenv("MEDSCAN_ADMIN_PASSWORD_HASH", "").strip()
    if not email or not password_hash:
        return None
    try:
        scheme = _password_context.identify(password_hash)
        if not scheme:
            return None
        _password_context.handler(scheme).from_string(password_hash)
    except (TypeError, ValueError):
        return None
    return email, password_hash


def _user_for_credentials(email: str, password_hash: str) -> dict:
    # Rotating the configured password also invalidates existing sessions.
    identity = hashlib.sha256(f"{email}\0{password_hash}".encode("utf-8")).hexdigest()
    open_id = f"local_{identity[:58]}"
    return {
        "id": 1,
        "openId": open_id,
        "email": email,
        "name": os.getenv("MEDSCAN_ADMIN_NAME", "MedScan administrator"),
        "role": "admin",
        "loginMethod": "email",
        "createdAt": _created_at,
        "lastSignedIn": _last_signed_in.get(open_id),
    }


def verify_simple_password(email: str, password: str) -> bool:
    """Verify the configured password hash without logging credentials."""
    credentials = _admin_credentials()
    if not credentials or email.strip().lower() != credentials[0]:
        return False
    try:
        return _password_context.verify(password, credentials[1])
    except (TypeError, ValueError, MissingBackendError):
        return False


def get_simple_user(email: str) -> Optional[dict]:
    """Get the configured owner; never expose the password hash in user data."""
    credentials = _admin_credentials()
    if not credentials or email.strip().lower() != credentials[0]:
        return None
    return _user_for_credentials(*credentials)


def update_last_signed_in(email: str):
    """Keep display-only last-login metadata for the current process."""
    user = get_simple_user(email)
    if user:
        _last_signed_in[user["openId"]] = datetime.now(timezone.utc)


async def create_session_for_user(email: str) -> str:
    """Create a signed session for the configured owner."""
    from server._core.sdk import sdk

    user = get_simple_user(email)
    if not user:
        raise ValueError("User not found")
    session_token = await sdk.create_session_token(
        user["openId"],
        {"name": user["name"] or user["email"], "expiresInMs": ONE_YEAR_MS},
    )
    update_last_signed_in(email)
    return session_token


def get_user_by_open_id(open_id: str) -> Optional[dict]:
    """Resolve a verified JWT identity only against the current owner settings."""
    credentials = _admin_credentials()
    if not credentials:
        return None
    user = _user_for_credentials(*credentials)
    return user if user["openId"] == open_id else None

