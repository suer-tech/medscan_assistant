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
    """Accept an API root, a versioned base, or a full completion endpoint."""
    base = (env.forge_api_url or "").strip().rstrip("/")
    if not base:
        base = "https://routerai.ru/api/v1"
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _assert_api_key():
    """Assert API key is configured"""
    if not env.forge_api_key:
        raise ValueError("BUILT_IN_FORGE_API_KEY is not configured")


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
        "model": env.llm_model,
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
    api_url = _resolve_api_url()
    api_key = env.forge_api_key
    
    # Keep credentials, prompts, images and response content out of logs.
    print(f"[LLM] Payload model: {payload.get('model')}")
    
    async with httpx.AsyncClient() as client:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://medscan-assistant.vercel.app",
            "X-Title": "Medical AI Analysis",
        }
        
        try:
            response = await client.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            
            if not response.is_success:
                # Provider error bodies may echo keys or submitted patient data.
                print(f"[LLM] Error response: HTTP {response.status_code}")
                
                raise ValueError(
                    f"LLM invoke failed: HTTP {response.status_code}"
                )
            
            result_json = response.json()
            print("[LLM] Response received successfully")
            return result_json
        except httpx.HTTPError as e:
            print(f"[LLM] HTTP error: {type(e).__name__}")
            raise ValueError("LLM HTTP request failed") from None
        except Exception as e:
            print(f"[LLM] Unexpected error: {type(e).__name__}")
            raise

