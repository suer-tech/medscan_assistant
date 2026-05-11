"""OAuth callback routes"""
from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException, status
from fastapi.responses import RedirectResponse
from server._core.sdk import sdk
from server._core.const import COOKIE_NAME, ONE_YEAR_MS
from server._core.cookies import get_session_cookie_options
import server.db as db_module

router = APIRouter()


@router.get("/api/oauth/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None
):
    """OAuth callback endpoint"""
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="code and state are required"
        )
    
    try:
        token_response = await sdk.exchange_code_for_token(code, state)
        user_info = await sdk.get_user_info(token_response.accessToken)
        
        if not user_info.openId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="openId missing from user info"
            )
        
        from datetime import datetime
        await db_module.upsert_user({
            "openId": user_info.openId,
            "name": user_info.name,
            "email": user_info.email,
            "loginMethod": user_info.loginMethod or user_info.platform,
            "lastSignedIn": datetime.utcnow(),
        })
        
        session_token = await sdk.create_session_token(
            user_info.openId,
            {
                "name": user_info.name or "",
                "expiresInMs": ONE_YEAR_MS,
            }
        )
        
        cookie_options = get_session_cookie_options(request)
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            COOKIE_NAME,
            session_token,
            max_age=ONE_YEAR_MS // 1000,
            **cookie_options
        )
        return response
    except Exception as error:
        print(f"[OAuth] Callback failed: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth callback failed"
        )

