"""SDK for OAuth and JWT authentication"""
import base64
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
from jose import jwt, JWTError
from fastapi import Request, HTTPException, status
from server._core.env import env
from server._core.const import AXIOS_TIMEOUT_MS, COOKIE_NAME, ONE_YEAR_MS
from server._core.types.manus_types import (
    ExchangeTokenRequest,
    ExchangeTokenResponse,
    GetUserInfoRequest,
    GetUserInfoResponse,
    GetUserInfoWithJwtRequest,
    GetUserInfoWithJwtResponse,
)
from server.models import User
import server.db as db_module


class SessionPayload:
    """Session token payload"""
    def __init__(self, open_id: str, app_id: str, name: str):
        self.openId = open_id
        self.appId = app_id
        self.name = name


class OAuthService:
    """OAuth service for token exchange and user info"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=AXIOS_TIMEOUT_MS / 1000,
        )
        print(f"[OAuth] Initialized with baseURL: {base_url}")
        if not base_url:
            print("[OAuth] ERROR: OAUTH_SERVER_URL is not configured!")
    
    def _decode_state(self, state: str) -> str:
        """Decode base64 state"""
        return base64.b64decode(state).decode('utf-8')
    
    async def get_token_by_code(self, code: str, state: str) -> ExchangeTokenResponse:
        """Exchange authorization code for token"""
        redirect_uri = self._decode_state(state)
        payload = ExchangeTokenRequest(
            clientId=env.app_id,
            grantType="authorization_code",
            code=code,
            redirectUri=redirect_uri,
        )
        
        response = await self.client.post(
            "/webdev.v1.WebDevAuthPublicService/ExchangeToken",
            json=payload.dict(),
        )
        response.raise_for_status()
        return ExchangeTokenResponse(**response.json())
    
    async def getUserInfoByToken(self, token: ExchangeTokenResponse) -> GetUserInfoResponse:
        """Get user info by access token"""
        payload = GetUserInfoRequest(accessToken=token.accessToken)
        response = await self.client.post(
            "/webdev.v1.WebDevAuthPublicService/GetUserInfo",
            json=payload.dict(),
        )
        response.raise_for_status()
        return GetUserInfoResponse(**response.json())


class SDKServer:
    """Main SDK server for authentication"""
    
    def __init__(self):
        self.oauth_service = OAuthService(env.oauth_server_url)
    
    def _derive_login_method(self, platforms: Any, fallback: Optional[str]) -> Optional[str]:
        """Derive login method from platforms"""
        if fallback and len(fallback) > 0:
            return fallback
        if not isinstance(platforms, list) or len(platforms) == 0:
            return None
        
        platform_set = {p for p in platforms if isinstance(p, str)}
        if "REGISTERED_PLATFORM_EMAIL" in platform_set:
            return "email"
        if "REGISTERED_PLATFORM_GOOGLE" in platform_set:
            return "google"
        if "REGISTERED_PLATFORM_APPLE" in platform_set:
            return "apple"
        if "REGISTERED_PLATFORM_MICROSOFT" in platform_set or "REGISTERED_PLATFORM_AZURE" in platform_set:
            return "microsoft"
        if "REGISTERED_PLATFORM_GITHUB" in platform_set:
            return "github"
        
        first = next(iter(platform_set), None)
        return first.lower() if first else None
    
    async def exchange_code_for_token(self, code: str, state: str) -> ExchangeTokenResponse:
        """Exchange OAuth code for token"""
        return await self.oauth_service.get_token_by_code(code, state)
    
    async def get_user_info(self, access_token: str) -> GetUserInfoResponse:
        """Get user info using access token"""
        token_response = ExchangeTokenResponse(accessToken=access_token, tokenType="", expiresIn=0, scope="", idToken="")
        data = await self.oauth_service.getUserInfoByToken(token_response)
        
        # Extract platforms from response if available
        platforms = getattr(data, 'platforms', None) if hasattr(data, 'platforms') else None
        platform = data.platform or getattr(data, 'platform', None)
        
        login_method = self._derive_login_method(platforms, platform)
        
        # Create response with login method
        response_dict = data.dict()
        response_dict['platform'] = login_method
        response_dict['loginMethod'] = login_method
        
        return GetUserInfoResponse(**response_dict)
    
    def _get_session_secret(self) -> bytes:
        """Get session secret for JWT"""
        return env.cookie_secret.encode('utf-8')
    
    async def create_session_token(
        self,
        open_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create session token for user"""
        if options is None:
            options = {}
        
        return await self.sign_session(
            SessionPayload(open_id, env.app_id, options.get("name", "")),
            options
        )
    
    async def sign_session(
        self,
        payload: SessionPayload,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Sign session JWT"""
        if options is None:
            options = {}
        
        issued_at = datetime.utcnow()
        expires_in_ms = options.get("expiresInMs", ONE_YEAR_MS)
        expiration = issued_at + timedelta(milliseconds=expires_in_ms)
        secret_key = self._get_session_secret()
        
        token_data = {
            "openId": payload.openId,
            "appId": payload.appId,
            "name": payload.name,
            "exp": expiration,
            "iat": issued_at,
        }
        
        return jwt.encode(token_data, secret_key, algorithm="HS256")
    
    async def verify_session(self, cookie_value: Optional[str]) -> Optional[SessionPayload]:
        """Verify session cookie"""
        if not cookie_value:
            print("[Auth] Missing session cookie")
            return None
        
        try:
            secret_key = self._get_session_secret()
            payload = jwt.decode(cookie_value, secret_key, algorithms=["HS256"])
            
            open_id = payload.get("openId")
            app_id = payload.get("appId", "")  # appId может быть пустым для простой аутентификации
            name = payload.get("name", "")
            
            if not open_id:
                print("[Auth] Session payload missing openId")
                return None
            
            # Для простой аутентификации appId может быть пустым
            # Используем пустую строку как значение по умолчанию
            if not app_id:
                app_id = ""
            if not name:
                name = open_id  # Используем openId как имя, если name не указан
            
            print(f"[Auth] Session verified: openId={open_id}, appId={app_id or '(empty)'}, name={name}")
            
            return SessionPayload(open_id, app_id, name)
        except JWTError as error:
            print(f"[Auth] Session verification failed: {error}")
            return None
    
    async def get_user_info_with_jwt(self, jwt_token: str) -> GetUserInfoWithJwtResponse:
        """Get user info using JWT token"""
        payload = GetUserInfoWithJwtRequest(
            jwtToken=jwt_token,
            projectId=env.app_id,
        )
        
        async with httpx.AsyncClient(timeout=AXIOS_TIMEOUT_MS / 1000) as client:
            response = await client.post(
                f"{env.oauth_server_url}/webdev.v1.WebDevAuthPublicService/GetUserInfoWithJwt",
                json=payload.dict(),
            )
            response.raise_for_status()
            data = response.json()
            
            platforms = data.get('platforms')
            platform = data.get('platform')
            login_method = self._derive_login_method(platforms, platform)
            
            data['platform'] = login_method
            data['loginMethod'] = login_method
            
            return GetUserInfoWithJwtResponse(**data)
    
    async def authenticate_request(self, request: Request) -> User:
        """Authenticate request and return user"""
        cookies = request.cookies
        session_cookie = cookies.get(COOKIE_NAME)
        session = await self.verify_session(session_cookie)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid session cookie"
            )
        
        session_user_id = session.openId
        signed_in_at = datetime.utcnow()
        user = await db_module.get_user_by_open_id(session_user_id)
        
        # If user not in DB, sync from OAuth server
        if not user:
            try:
                user_info = await self.get_user_info_with_jwt(session_cookie or "")
                await db_module.upsert_user({
                    "openId": user_info.openId,
                    "name": user_info.name,
                    "email": user_info.email,
                    "loginMethod": user_info.loginMethod or user_info.platform,
                    "lastSignedIn": signed_in_at,
                })
                user = await db_module.get_user_by_open_id(user_info.openId)
            except Exception as error:
                print(f"[Auth] Failed to sync user from OAuth: {error}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Failed to sync user info"
                )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not found"
            )
        
        # Update last signed in
        await db_module.upsert_user({
            "openId": user.openId,
            "lastSignedIn": signed_in_at,
        })
        
        return user


# Global SDK instance
sdk = SDKServer()

