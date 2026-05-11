"""FastAPI dependencies for authentication and authorization"""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from server._core.sdk import sdk
from server._core.const import UNAUTHED_ERR_MSG, NOT_ADMIN_ERR_MSG, COOKIE_NAME
from server._core.simple_auth import get_user_by_open_id


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user from request (optional, for public endpoints) - простая аутентификация"""
    try:
        # Простая аутентификация через сессионные cookies
        cookies = request.cookies
        session_cookie = cookies.get(COOKIE_NAME)
        
        print(f"[Auth] get_current_user called for {request.url.path}")
        print(f"[Auth] Cookies received: {list(cookies.keys())}")
        print(f"[Auth] Session cookie present: {session_cookie is not None}")
        
        if session_cookie:
            # Verify session and get user
            session = await sdk.verify_session(session_cookie)
            if session:
                print(f"[Auth] Session verified, openId: {session.openId}")
                user = get_user_by_open_id(session.openId)
                if user:
                    print(f"[Auth] User found: {user.get('email')}")
                    return user
                else:
                    print(f"[Auth] User not found for openId: {session.openId}")
            else:
                print(f"[Auth] Session verification failed")
        else:
            print(f"[Auth] No session cookie found")
        
        return None
    except HTTPException:
        return None
    except Exception as e:
        print(f"[Auth] Error in get_current_user: {e}")
        import traceback
        traceback.print_exc()
        return None


async def require_user(request: Request) -> Dict[str, Any]:
    """Require authenticated user"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UNAUTHED_ERR_MSG
        )
    return user


async def require_admin(request: Request) -> Dict[str, Any]:
    """Require admin user"""
    user = await require_user(request)
    user_role = user.get("role") if isinstance(user, dict) else (user.role.value if hasattr(user, 'role') else str(user.role))
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=NOT_ADMIN_ERR_MSG
        )
    return user
