"""Environment configuration (Refreshed by AI)"""
import os
import secrets
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from server directory
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


class ENV:
    """Environment variables configuration"""

    def __init__(self):
        # A development-only fallback, never shared between processes or deploys.
        self._development_cookie_secret = secrets.token_urlsafe(48)
    
    @staticmethod
    def _get_env(key: str, default: str = "") -> str:
        return os.getenv(key, default)
    
    @property
    def app_id(self) -> str:
        return self._get_env("VITE_APP_ID")
    
    @property
    def cookie_secret(self) -> str:
        secret = self._get_env("JWT_SECRET")
        if self.is_production:
            if len(secret.strip().encode("utf-8")) < 32:
                raise RuntimeError("JWT_SECRET must be configured with at least 32 bytes in production")
            return secret
        return secret or self._development_cookie_secret
    
    @property
    def database_url(self) -> str:
        return self._get_env("DATABASE_URL")
    
    @property
    def oauth_server_url(self) -> str:
        return self._get_env("OAUTH_SERVER_URL")
    
    @property
    def owner_open_id(self) -> str:
        return self._get_env("OWNER_OPEN_ID")
    
    @property
    def is_production(self) -> bool:
        return (
            os.getenv("NODE_ENV", "").lower() == "production"
            or os.getenv("VERCEL", "") == "1"
            or os.getenv("VERCEL_ENV", "").lower() in {"production", "preview"}
        )
    
    @property
    def forge_api_url(self) -> str:
        return self._get_env("BUILT_IN_FORGE_API_URL", "https://routerai.ru/api/v1")
    
    @property
    def forge_api_key(self) -> str:
        return self._get_env(
            "BUILT_IN_FORGE_API_KEY",
            ""
        )
    
    @property
    def llm_model(self) -> str:
        return self._get_env("LLM_MODEL", "google/gemini-2.5-flash-lite")


# Global instance
env = ENV()

