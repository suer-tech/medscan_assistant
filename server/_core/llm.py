"""LLM API integration"""
from typing import List, Dict, Any, Optional, Union
from server._core.env import env

# Type definitions
Role = str  # "system" | "user" | "assistant" | "tool" | "function"

TextContent = Dict[str, str]  # {"type": "text", "text": "..."}
ImageContent = Dict[str, Any]  # {"type": "image_url", "image_url": {...}}
FileContent = Dict[str, Any]  # {"type": "file_url", "file_url": {...}}

MessageContent = Union[str, TextContent, ImageContent, FileContent, List[Union[TextContent, ImageContent, FileContent]]]

Message = Dict[str, Any]  # {"role": Role, "content": MessageContent, ...}

Tool = Dict[str, Any]  # {"type": "function", "function": {...}}

InvokeResult = Dict[str, Any]


def _ensure_array(value: MessageContent) -> List[Union[TextContent, ImageContent, FileContent]]:
    """Ensure content is an array"""
    if isinstance(value, str):
        return [{"type": "text", "text": value}]
    if isinstance(value, list):
        return value
    return [value]


def _normalize_content_part(part: MessageContent) -> Union[TextContent, ImageContent, FileContent]:
    """Normalize content part"""
    if isinstance(part, str):
        return {"type": "text", "text": part}
    if isinstance(part, dict):
        return part
    raise ValueError("Unsupported message content part")


def _normalize_message(message: Message) -> Dict[str, Any]:
    """Normalize message for API"""
    role = message.get("role")
    name = message.get("name")
    tool_call_id = message.get("tool_call_id")
    content = message.get("content", "")
    
    if role in ("tool", "function"):
        content_parts = _ensure_array(content)
        content_str = "\n".join(
            part if isinstance(part, str) else str(part)
            for part in content_parts
        )
        result = {
            "role": role,
            "content": content_str,
        }
        if name:
            result["name"] = name
        if tool_call_id:
            result["tool_call_id"] = tool_call_id
        return result
    
    content_parts = _ensure_array(content)
    normalized_parts = [_normalize_content_part(part) for part in content_parts]
    
    # If only text content, collapse to string
    if len(normalized_parts) == 1 and normalized_parts[0].get("type") == "text":
        result = {
            "role": role,
            "content": normalized_parts[0]["text"],
        }
    else:
        result = {
            "role": role,
            "content": normalized_parts,
        }
    
    if name:
        result["name"] = name
    
    return result


def _resolve_api_url() -> str:
    """Resolve LLM API URL"""
    if env.forge_api_url and env.forge_api_url.strip():
        base = env.forge_api_url.rstrip("/")
        return f"{base}/v1/chat/completions"
    return "https://openrouter.ai/api/v1/chat/completions"


def _assert_api_key():
    """Assert API key is configured"""
    if not env.forge_api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured")


async def invoke_llm(
    messages: List[Message],
    tools: Optional[List[Tool]] = None,
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    max_tokens: Optional[int] = None,
    response_format: Optional[Dict[str, Any]] = None,
) -> InvokeResult:
    """Invoke LLM API"""
    _assert_api_key()
    
    payload: Dict[str, Any] = {
        "model": "openai/gpt-5-mini",
        "messages": [_normalize_message(msg) for msg in messages],
    }
    
    if tools and len(tools) > 0:
        payload["tools"] = tools
    
    if tool_choice:
        payload["tool_choice"] = tool_choice
    
    payload["max_tokens"] = max_tokens or 32768
    
    if response_format:
        payload["response_format"] = response_format
    
    import httpx
    import json
    api_url = _resolve_api_url()
    api_key = env.forge_api_key
    
    # Log request details (without exposing full key)
    print(f"[LLM] Request to: {api_url}")
    print(f"[LLM] API key present: {bool(api_key)}, key prefix: {api_key[:15]}..." if api_key else "[LLM] API key: NOT SET")
    print(f"[LLM] Payload model: {payload.get('model')}")
    
    async with httpx.AsyncClient() as client:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://ai.teamidea.ru",
            "X-Title": "Medical AI Analysis",
        }
        print(f"[LLM] Headers: {list(headers.keys())}")
        
        try:
            response = await client.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            
            if not response.is_success:
                error_text = await response.aread()
                try:
                    error_json = json.loads(error_text.decode())
                    error_message = error_json.get("error", {}).get("message", error_text.decode())
                    error_code = error_json.get("error", {}).get("code", "")
                except (json.JSONDecodeError, AttributeError):
                    error_message = error_text.decode() if error_text else "No error details"
                    error_code = ""
                
                print(f"[LLM] Error response: {response.status_code} {response.reason_phrase}")
                print(f"[LLM] Error message: {error_message}")
                print(f"[LLM] Error code: {error_code}")
                print(f"[LLM] Full error response: {error_text.decode()[:500] if error_text else 'No response body'}")
                
                raise ValueError(
                    f"LLM invoke failed: {response.status_code} {response.reason_phrase} – {error_message}"
                )
            
            return response.json()
        except httpx.HTTPError as e:
            print(f"[LLM] HTTP error: {e}")
            raise ValueError(f"LLM HTTP error: {e}")
        except Exception as e:
            print(f"[LLM] Unexpected error: {type(e).__name__}: {e}")
            raise

