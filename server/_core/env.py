"""Environment configuration"""
import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from server directory
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


class ENV:
    """Environment variables configuration"""
    
    @staticmethod
    def _get_env(key: str, default: str = "") -> str:
        return os.getenv(key, default)
    
    @property
    def app_id(self) -> str:
        return self._get_env("VITE_APP_ID")
    
    @property
    def cookie_secret(self) -> str:
        return self._get_env("JWT_SECRET")
    
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
        return os.getenv("NODE_ENV", "").lower() == "production"
    
    @property
    def forge_api_url(self) -> str:
        return self._get_env("BUILT_IN_FORGE_API_URL", "https://openrouter.ai/api")
    
    @property
    def forge_api_key(self) -> str:
        return self._get_env(
            "BUILT_IN_FORGE_API_KEY",
            ""
        )


# Global instance
env = ENV()

