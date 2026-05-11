"""Simple authentication for MVP - single user, no database"""
from typing import Optional
from datetime import datetime
from server._core.sdk import sdk
from server._core.const import ONE_YEAR_MS

# Simple user storage (in-memory for MVP)
# In production, this would be in a database
SIMPLE_USERS = {
    "example@mail.ru": {
        "id": 1,
        "openId": "local_example_at_mail.ru",
        "email": "example@mail.ru",
        "name": "example",
        "passwordHash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqJqJqJqJq",  # hash (not used, password checked in VALID_PASSWORDS)
        "role": "user",
        "loginMethod": "email",
        "createdAt": datetime.utcnow(),
        "lastSignedIn": None,
    }
}

# Password: Kp9mX2vN7qR4wL8tY5zA
# To generate: from passlib.context import CryptContext; pwd_context = CryptContext(schemes=["bcrypt"]); print(pwd_context.hash("password"))
# For now, using a simple check
VALID_PASSWORDS = {
    "example@mail.ru": ["Kp9mX2vN7qR4wL8tY5zA", "123"]
}


def verify_simple_password(email: str, password: str) -> bool:
    """Verify password for simple auth"""
    # Normalize email: trim whitespace and convert to lowercase
    email = email.strip().lower()
    password = password.strip()
    
    valid_pass = VALID_PASSWORDS.get(email)
    
    if isinstance(valid_pass, list):
        result = password in valid_pass
        expected_password = valid_pass
    else:
        result = valid_pass == password
        expected_password = valid_pass
    
    print(f"[SimpleAuth] verify_simple_password: email='{email}', expected='{expected_password}', provided='{password}', match={result}")
    
    return result


def get_simple_user(email: str) -> Optional[dict]:
    """Get user by email"""
    return SIMPLE_USERS.get(email)


def update_last_signed_in(email: str):
    """Update last signed in time"""
    if email in SIMPLE_USERS:
        SIMPLE_USERS[email]["lastSignedIn"] = datetime.utcnow()


async def create_session_for_user(email: str) -> str:
    """Create session token for user"""
    user = get_simple_user(email)
    if not user:
        raise ValueError("User not found")
    
    session_token = await sdk.create_session_token(
        user["openId"],
        {
            "name": user["name"] or email,
            "expiresInMs": ONE_YEAR_MS,
        }
    )
    
    update_last_signed_in(email)
    return session_token


def get_user_by_open_id(open_id: str) -> Optional[dict]:
    """Get user by openId"""
    for user in SIMPLE_USERS.values():
        if user["openId"] == open_id:
            return user
    return None

