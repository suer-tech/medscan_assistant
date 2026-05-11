"""Script to create test user with password"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from server.db import upsert_user, get_user_by_email
from datetime import datetime

async def create_test_user():
    """Create test user example@mail.ru with password 123"""
    email = "example@mail.ru"
    password = "123"
    
    # Check if user exists
    user = await get_user_by_email(email)
    
    if user:
        print(f"User {email} already exists. Updating password...")
        open_id = user.openId
    else:
        open_id = f"local_{email.replace('@', '_at_')}"
        print(f"Creating new user {email}...")
    
    await upsert_user({
        "openId": open_id,
        "email": email,
        "name": email.split("@")[0],
        "password": password,  # Will be hashed automatically
        "loginMethod": "email",
        "lastSignedIn": datetime.utcnow(),
    })
    
    print(f"User {email} created/updated with password")
    print(f"  OpenId: {open_id}")

if __name__ == "__main__":
    asyncio.run(create_test_user())

