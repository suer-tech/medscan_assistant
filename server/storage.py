"""Storage operations for file uploads"""
from typing import Union
import httpx
from server._core.env import env


def _get_storage_config():
    """Get storage configuration"""
    base_url = env.forge_api_url
    api_key = env.forge_api_key
    
    if not base_url or not api_key:
        raise ValueError(
            "Storage proxy credentials missing: set BUILT_IN_FORGE_API_URL and BUILT_IN_FORGE_API_KEY"
        )
    
    return {
        "base_url": base_url.rstrip("/"),
        "api_key": api_key,
    }


def _normalize_key(rel_key: str) -> str:
    """Normalize storage key"""
    return rel_key.lstrip("/")


def _build_upload_url(base_url: str, rel_key: str) -> str:
    """Build upload URL"""
    base = base_url.rstrip("/") + "/"
    url = f"{base}v1/storage/upload"
    return f"{url}?path={_normalize_key(rel_key)}"


async def _build_download_url(base_url: str, rel_key: str, api_key: str) -> str:
    """Build download URL"""
    base = base_url.rstrip("/") + "/"
    url = f"{base}v1/storage/downloadUrl"
    download_url = f"{url}?path={_normalize_key(rel_key)}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            download_url,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        data = response.json()
        return data["url"]


async def storage_put(
    rel_key: str,
    data: Union[bytes, str],
    content_type: str = "application/octet-stream"
) -> dict:
    """Upload file to storage"""
    config = _get_storage_config()
    key = _normalize_key(rel_key)
    upload_url = _build_upload_url(config["base_url"], key)
    
    # Prepare file data
    if isinstance(data, str):
        file_data = data.encode('utf-8')
    else:
        file_data = data
    
    # Get filename from key
    filename = key.split("/")[-1] if "/" in key else key
    
    # Create multipart form data
    files = {
        "file": (filename, file_data, content_type)
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            upload_url,
            headers={"Authorization": f"Bearer {config['api_key']}"},
            files=files,
        )
        
        if not response.is_success:
            error_text = await response.aread()
            raise ValueError(
                f"Storage upload failed ({response.status_code} {response.reason_phrase}): {error_text.decode()}"
            )
        
        result = response.json()
        return {"key": key, "url": result["url"]}


async def storage_get(rel_key: str) -> dict:
    """Get download URL for file"""
    config = _get_storage_config()
    key = _normalize_key(rel_key)
    url = await _build_download_url(config["base_url"], key, config["api_key"])
    return {"key": key, "url": url}

