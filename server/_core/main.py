"""Main FastAPI application"""
import os
import socket
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from server._core.env import env
from server._core.system_router import router as system_router
from server.routers import router as app_router

app = FastAPI(title="Medical AI X-Ray Analysis API")

# CORS middleware
# Важно: нельзя использовать allow_origins=["*"] с allow_credentials=True
# Нужно указать конкретные origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4000",
        "http://127.0.0.1:4000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4001",
        "http://127.0.0.1:4001",
        "http://localhost:4002",
        "http://127.0.0.1:4002",
        "https://medscan-assistant.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Request logging middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        path = request.url.path
        method = request.method
        
        # Log metadata only: request bodies can contain passwords and medical data.
        print(f"\n[Request] {method} {path}")
        
        response = await call_next(request)
        print(f"[Response] {method} {path} -> {response.status_code}")
        return response

app.add_middleware(LoggingMiddleware)


# Убрали tRPC middleware - теперь используем простой REST API


def is_port_available(port: int) -> bool:
    """Check if port is available"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def find_available_port(start_port: int = 3000) -> int:
    """Find available port starting from start_port"""
    for port in range(start_port, start_port + 20):
        if is_port_available(port):
            return port
    raise RuntimeError(f"No available port found starting from {start_port}")


# Register routers
app.include_router(system_router)
app.include_router(app_router)

# Static files serving (only in production, not in backend-only mode)
backend_only = os.getenv("BACKEND_ONLY", "").lower() == "true"

if not backend_only:
    # Check if dist/public exists
    dist_public = Path(__file__).parent.parent.parent / "dist" / "public"
    if dist_public.exists():
        app.mount("/", StaticFiles(directory=str(dist_public), html=True), name="static")


@app.get("/")
async def root():
    """Root endpoint"""
    if backend_only:
        return {"message": "Backend API only mode"}
    # In production, static files will be served
    dist_public = Path(__file__).parent.parent.parent / "dist" / "public" / "index.html"
    if dist_public.exists():
        return FileResponse(str(dist_public))
    return {"message": "Frontend not built"}


if __name__ == "__main__":
    import uvicorn
    
    preferred_port = int(os.getenv("PORT", "4001"))
    port = find_available_port(preferred_port)
    
    if port != preferred_port:
        print(f"Port {preferred_port} is busy, using port {port} instead")
    
    uvicorn.run(
        "server._core.main:app",
        host="0.0.0.0",
        port=port,
        reload=not env.is_production,
    )

