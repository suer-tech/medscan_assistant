"""System router for health checks and admin operations"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from server._core.dependencies import require_admin
from server._core.notification import notify_owner
from server.models import User

router = APIRouter()


class HealthInput(BaseModel):
    timestamp: int = Field(..., ge=0, description="timestamp cannot be negative")


class HealthOutput(BaseModel):
    ok: bool


class NotifyOwnerInput(BaseModel):
    title: str = Field(..., min_length=1, description="title is required")
    content: str = Field(..., min_length=1, description="content is required")


class NotifyOwnerOutput(BaseModel):
    success: bool


@router.post("/api/trpc/system.health", response_model=HealthOutput)
async def health(input_data: HealthInput):
    """Health check endpoint"""
    return {"ok": True}


@router.post("/api/trpc/system.notifyOwner", response_model=NotifyOwnerOutput)
async def notify_owner_endpoint(
    input_data: NotifyOwnerInput,
    user: User = Depends(require_admin)
):
    """Notify owner endpoint (admin only)"""
    delivered = await notify_owner(input_data.title, input_data.content)
    return {"success": delivered}

