"""Cookie handling utilities"""
from typing import Dict, Optional
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
    
    # For domain medscan.krmu.edu.kz, assume HTTPS (it's always served over HTTPS)
    host = request.headers.get("host", "").split(":")[0]
    if host == "medscan.krmu.edu.kz":
        return True
    
    return False


def get_session_cookie_options(request: Request) -> Dict[str, any]:
    """Get session cookie options based on request"""
    host = request.headers.get("host", "").split(":")[0]
    is_local = host in LOCAL_HOSTS or host == "::1" or is_ip_address(host)
    is_secure = is_secure_request(request)
    
    # For localhost and IP addresses, use lax samesite without secure
    # Важно: не указываем domain для localhost/IP, чтобы cookie работал
    # SameSite=Lax работает для HTTP запросов с IP адресами
    if is_local or is_ip_address(host):
        return {
            "httponly": True,
            "path": "/",
            "samesite": "lax",
            "secure": False,
            # Не указываем domain для localhost/IP - это позволит cookie работать
        }
    else:
        # For domain names
        # If HTTPS, use secure=True (required for SameSite=None)
        # If HTTP, use SameSite=Lax (works for same-site requests)
        if is_secure:
            return {
                "httponly": True,
                "path": "/",
                "samesite": "none",
                "secure": True,  # Required for SameSite=None on HTTPS
            }
        else:
            return {
                "httponly": True,
                "path": "/",
                "samesite": "lax",  # Lax works for same-site HTTP requests
                "secure": False,
            }

