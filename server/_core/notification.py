"""Notification service"""
from typing import Dict, Any
from server._core.env import env
import httpx

TITLE_MAX_LENGTH = 1200
CONTENT_MAX_LENGTH = 20000


def _validate_payload(title: str, content: str) -> Dict[str, str]:
    """Validate notification payload"""
    title = title.strip()
    content = content.strip()
    
    if not title:
        raise ValueError("Notification title is required.")
    if not content:
        raise ValueError("Notification content is required.")
    if len(title) > TITLE_MAX_LENGTH:
        raise ValueError(f"Notification title must be at most {TITLE_MAX_LENGTH} characters.")
    if len(content) > CONTENT_MAX_LENGTH:
        raise ValueError(f"Notification content must be at most {CONTENT_MAX_LENGTH} characters.")
    
    return {"title": title, "content": content}


def _build_endpoint_url(base_url: str) -> str:
    """Build notification endpoint URL"""
    normalized_base = base_url.rstrip("/") + "/"
    return f"{normalized_base}webdevtoken.v1.WebDevService/SendNotification"


async def notify_owner(title: str, content: str) -> bool:
    """Send notification to owner"""
    try:
        payload = _validate_payload(title, content)
    except ValueError as e:
        raise ValueError(str(e))
    
    if not env.forge_api_url:
        raise ValueError("Notification service URL is not configured.")
    
    if not env.forge_api_key:
        raise ValueError("Notification service API key is not configured.")
    
    endpoint = _build_endpoint_url(env.forge_api_url)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                headers={
                    "accept": "application/json",
                    "authorization": f"Bearer {env.forge_api_key}",
                    "content-type": "application/json",
                    "connect-protocol-version": "1",
                },
                json=payload,
                timeout=30.0,
            )
            
            if not response.is_success:
                detail = await response.aread()
                print(
                    f"[Notification] Failed to notify owner ({response.status_code} {response.reason_phrase})"
                    f"{f': {detail.decode()}' if detail else ''}"
                )
                return False
            
            return True
    except Exception as error:
        print(f"[Notification] Error calling notification service: {error}")
        return False

