"""Cookie handling utilities"""
from typing import Any, Dict
from fastapi import Request

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def is_ip_address(host: str) -> bool:
    """Check if host is an IP address"""
    # Basic IPv4 check and IPv6 presence detection
    if len(host.split(".")) == 4 and all(part.isdigit() for part in host.split(".")):
        return True
    return ":" in host


def is_secure_request(request: Request) -> bool:
    """Check if request is secure (HTTPS)"""
    # Check direct HTTPS
    if request.url.scheme == "https":
        return True
    
    # Check X-Forwarded-Proto header (from proxy)
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if forwarded_proto:
        proto_list = forwarded_proto.split(",")
        if any(proto.strip().lower() == "https" for proto in proto_list):
            return True
    
    # Check X-Forwarded-Scheme (alternative header)
    forwarded_scheme = request.headers.get("x-forwarded-scheme")
    if forwarded_scheme and forwarded_scheme.lower() == "https":
        return True
    
    return False


def get_session_cookie_options(request: Request) -> Dict[str, Any]:
    """Host-only cookies for the same-origin frontend/API, including logout."""
    return {
        "httponly": True,
        "path": "/",
        "samesite": "lax",
        "secure": is_secure_request(request),
    }

