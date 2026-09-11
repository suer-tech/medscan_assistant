"""Main API routers"""
from typing import List, Optional
import os
import base64
import binascii
import io
import warnings
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError
# Убрали импорты моделей - теперь используем файловое хранилище
from server._core.dependencies import get_current_user, require_user
from server._core.cookies import get_session_cookie_options
from server._core.const import COOKIE_NAME, ONE_YEAR_MS
if os.getenv("VERCEL") or os.getenv("MEDSCAN_STORAGE") == "postgres":
    import server.postgres_storage as db
else:
    import server.file_storage as db
# Убрали storage_put - для MVP используем локальное хранилище
from server.openai import analyze_xray_image, analyze_template_form
from server.pdf import generate_pdf
from server.models import StudyType, StudyStatus, ChatMessageRole
# Optional nanoid import
try:
    from nanoid import generate
except ImportError:
    import secrets
    import string
    def generate(size=21):
        alphabet = string.ascii_letters + string.digits + '-_'
        return ''.join(secrets.choice(alphabet) for _ in range(size))

router = APIRouter()


@router.get("/api/health")
async def health_check():
    """Read-only readiness check; no credentials or patient records."""
    try:
        if hasattr(db, "health_check"):
            storage = await db.health_check()
        else:
            storage = {"database": "local_json", "persistent": False}
        from server._core.env import env
        from server._core.simple_auth import get_simple_user
        admin_email = os.getenv("MEDSCAN_ADMIN_EMAIL", "")
        return {"ok": True, **storage, "aiConfigured": bool(env.forge_api_key),
                "authConfigured": bool(get_simple_user(admin_email))}
    except Exception as error:
        print(f"[Health] Readiness failed ({type(error).__name__})")
        raise HTTPException(status_code=503, detail="Service configuration unavailable")


# Pydantic models for requests/responses
class StudyCreateInput(BaseModel):
    title: str = Field(..., min_length=1)
    studyType: str = Field(..., pattern="^(retinal_scan|optic_nerve|macular_analysis|free_query|template_form|ultrasound_thyroid|ultrasound_liver|lab_blood|brain|lungs|bone|eye)$")


class StudyCreateOutput(BaseModel):
    id: int


class StudyGetOutput(BaseModel):
    id: int
    userId: int
    title: str
    studyType: str
    status: str
    analysisResult: Optional[str]
    createdAt: str
    updatedAt: str
    images: List[dict]


class StudyUpdateInput(BaseModel):
    title: Optional[str] = None
    analysisResult: Optional[str] = None


class StudyUploadImageInput(BaseModel):
    imageData: str  # base64
    filename: str = Field(..., min_length=1, max_length=255)
    mimeType: str = Field(..., min_length=1, max_length=32)


class StudyUploadImageOutput(BaseModel):
    id: int
    url: str


MAX_IMAGE_BYTES = 3 * 1024 * 1024
IMAGE_FORMAT_MIMES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp", "GIF": "image/gif"}


def validate_study_image(data_url: str, declared_mime: str) -> tuple[bytes, str]:
    """Validate original raster bytes without resizing or recompressing them."""
    header, separator, encoded = data_url.partition(",")
    mime = declared_mime.strip().lower()
    if mime not in IMAGE_FORMAT_MIMES.values() or separator != "," or header.lower() != f"data:{mime};base64":
        raise HTTPException(status_code=400, detail="Допустимы только изображения PNG, JPEG, WebP и GIF в формате base64 data URL")
    if len(encoded) > 4 * ((MAX_IMAGE_BYTES + 2) // 3):
        raise HTTPException(status_code=413, detail="Размер исходного изображения не должен превышать 3 МБ")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Некорректные base64-данные изображения") from None
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Размер исходного изображения не должен превышать 3 МБ")
    if not content:
        raise HTTPException(status_code=400, detail="Файл изображения пуст")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                actual_mime = IMAGE_FORMAT_MIMES.get(image.format)
                if actual_mime != mime:
                    raise ValueError("Image format does not match its declared MIME type")
                image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(status_code=400, detail="Некорректное или неподдерживаемое растровое изображение") from None
    return content, mime


def study_image_metadata(study_id: int, image: dict) -> dict:
    """Expose an authenticated image URL; retain data URLs only in storage."""
    return {**image, "url": f"/api/studies/{study_id}/images/{image['id']}"}


class StudyAnalyzeInput(BaseModel):
    studyId: int


class StudyAnalyzeOutput(BaseModel):
    success: bool
    analysisResult: str


class StudyDeleteInput(BaseModel):
    id: int


class StudyDownloadPDFInput(BaseModel):
    id: int


class StudyDownloadPDFOutput(BaseModel):
    pdf: str  # base64
    filename: str


class ChatGetMessagesInput(BaseModel):
    studyId: int


class ChatSendMessageInput(BaseModel):
    message: str = Field(..., min_length=1)


class ChatSendMessageOutput(BaseModel):
    success: bool
    message: str


# Auth endpoints - простые REST API
@router.get("/api/auth/me")
async def auth_me(request: Request, user: Optional[dict] = Depends(get_current_user)):
    """Get current user"""
    print(f"[Auth] auth.me called, user: {user is not None}, cookies: {list(request.cookies.keys())}")
    return user or None


class LoginInput(BaseModel):
    email: str
    password: str


class LoginOutput(BaseModel):
    success: bool
    user: Optional[dict] = None


@router.post("/api/auth/login")
async def auth_login(login_data: LoginInput, request: Request):
    """Login with email and password - простой REST API"""
    # Простой парсинг - FastAPI автоматически парсит JSON в LoginInput
    email = login_data.email.strip().lower()
    password = login_data.password
    
    print("[Auth] Login attempt")
    
    # Simple authentication (no database for MVP)
    from server._core.simple_auth import (
        verify_simple_password,
        get_simple_user,
        create_session_for_user
    )
    
    # Verify password
    print("[Auth] Verifying password")
    
    if not verify_simple_password(email, password):
        print("[Auth] Password verification failed")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Get user
    user = get_simple_user(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create session token
    session_token = await create_session_for_user(email)
    
    cookie_options = get_session_cookie_options(request)
    
    # Return data directly - httpLink without transformer expects plain JSON
    response_data = {
        "success": True,
        "user": {
            "id": user["id"],
            "openId": user["openId"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        }
    }
    
    response_obj = JSONResponse(response_data)
    response_obj.set_cookie(
        COOKIE_NAME,
        session_token,
        max_age=ONE_YEAR_MS // 1000,
        **cookie_options
    )
    
    print("[Auth] Login succeeded; session cookie set")
    
    return response_obj


@router.post("/api/auth/logout")
async def auth_logout(request: Request):
    """Logout user"""
    cookie_options = get_session_cookie_options(request)
    response = JSONResponse({"success": True})
    response.delete_cookie(COOKIE_NAME, **cookie_options)
    return response


# Studies endpoints - простые REST API
@router.get("/api/studies")
async def studies_list(user: dict = Depends(require_user)):
    """Get all studies for user"""
    studies = await db.get_studies_by_user_id(user["id"])
    # Файловое хранилище возвращает словари, используем JSONResponse для правильного Content-Length
    # Это исправляет проблему ERR_CONTENT_LENGTH_MISMATCH
    return JSONResponse(content=studies)


class StudyGetInput(BaseModel):
    id: int


@router.get("/api/studies/{study_id}")
async def studies_get(study_id: int, user: dict = Depends(require_user)):
    """Get study by ID"""
    study = await db.get_study_by_id(study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    if study["userId"] != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    images = await db.get_study_images(study_id)
    # Добавляем изображения к исследованию
    result = study.copy()
    result["images"] = [study_image_metadata(study_id, image) for image in images]
    # Используем JSONResponse для правильного Content-Length
    return JSONResponse(content=result)


@router.post("/api/studies")
async def studies_create(input_data: StudyCreateInput, user: dict = Depends(require_user)):
    """Create new study"""
    study_id = await db.create_study({
        "userId": user["id"],
        "title": input_data.title,
        "studyType": input_data.studyType,
        "status": "draft",
    })
    return {"id": study_id}


@router.post("/api/studies/{study_id}/images")
async def studies_upload_image(study_id: int, input_data: StudyUploadImageInput, user: dict = Depends(require_user)):
    """Upload image for study"""
    study = await db.get_study_by_id(study_id)
    if not study or study["userId"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    image_bytes, image_mime = validate_study_image(input_data.imageData, input_data.mimeType)
    # Keep the original data URL for AI/PDF; do not return it in JSON responses.
    image_url = input_data.imageData
    
    # Save metadata to file storage
    image_id = await db.create_study_image({
        "studyId": study_id,
        "fileKey": f"studies/{user['id']}/{study_id}/{generate()}-{input_data.filename}",
        "url": image_url,
        "filename": input_data.filename,
        "mimeType": image_mime,
        "fileSize": len(image_bytes),
    })
    
    return {"id": image_id, "url": f"/api/studies/{study_id}/images/{image_id}"}


@router.get("/api/studies/{study_id}/images/{image_id}")
async def studies_get_image(study_id: int, image_id: int, user: dict = Depends(require_user)):
    """Serve one original raster, authorized through its owning study."""
    study = await db.get_study_by_id(study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    if study["userId"] != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    images = await db.get_study_images(study_id)
    image = next((item for item in images if item["id"] == image_id), None)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    image_bytes, image_mime = validate_study_image(image["url"], image["mimeType"])
    return Response(content=image_bytes, media_type=image_mime, headers={
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    })


class TemplateFieldInput(BaseModel):
    name: str
    value: str
    included: bool


class StudyAnalyzeInput(BaseModel):
    userQuery: Optional[str] = None
    template: Optional[List[TemplateFieldInput]] = None


@router.post("/api/studies/{study_id}/analyze")
async def studies_analyze(study_id: int, input_data: StudyAnalyzeInput = None, user: dict = Depends(require_user)):
    """Analyze study images"""
    print(f"\n" + "="*50)
    print(f"[STEP 1] Получен запрос на анализ: study_id={study_id}, user_id={user['id']}")
    
    study = await db.get_study_by_id(study_id)
    if not study or study["userId"] != user["id"]:
        print(f"[ERROR] Исследование не найдено или нет прав доступа")
        raise HTTPException(status_code=403, detail="Forbidden")
    
    print(f"[STEP 2] Загружено исследование: тип '{study['studyType']}'")
    
    images = await db.get_study_images(study_id)
    if len(images) == 0:
        print(f"[ERROR] К исследованию не прикреплено ни одного изображения")
        raise HTTPException(status_code=400, detail="No images uploaded")
    
    print(f"[STEP 3] Найдено изображений для анализа: {len(images)}")
    
    # Update status to analyzing
    await db.update_study(study_id, {"status": "analyzing"})
    
    try:
        # Get user query or template if provided
        user_query = input_data.userQuery if input_data and input_data.userQuery else None
        template = input_data.template if input_data and input_data.template else None
        
        # Analyze the first image
        if template:
            print(f"[STEP 4] Выбран режим анализа по шаблону (template mode)")
            # Convert Pydantic models to dicts
            template_dicts = [t.dict() if hasattr(t, 'dict') else t for t in template]
            analysis_result = await analyze_template_form(images[0]["url"], template_dicts)
        else:
            print(f"[STEP 4] Выбран режим стандартного анализа снимка (xray mode)")
            analysis_result = await analyze_xray_image(images[0]["url"], study["studyType"], user_query=user_query)
        
        print(f"[STEP 7] Ответ получен, обновляем статус в базе данных")
        # Update study with results
        await db.update_study(study_id, {
            "status": "completed",
            "analysisResult": analysis_result,
        })
        
        print(f"[STEP 8] Анализ успешно завершен!" + "\n" + "="*50)
        return {"success": True, "analysisResult": analysis_result}
    except Exception as error:
        # Upstream errors can contain submitted medical data or credentials.
        print(f"[Analyze] Error for study {study_id}: {type(error).__name__}")
        
        # Don't save error status if we already have a result (partial success)
        current_study = await db.get_study_by_id(study_id)
        if current_study and current_study.get("analysisResult"):
            # If result exists, keep it but mark as error
            await db.update_study(study_id, {"status": "error"})
        else:
            # No result yet, mark as error
            await db.update_study(study_id, {"status": "error"})
        
        raise HTTPException(
            status_code=500, 
            detail="Failed to analyze image"
        )


class StudyUpdateRequest(BaseModel):
    title: Optional[str] = None
    analysisResult: Optional[str] = None


@router.patch("/api/studies/{study_id}")
async def studies_update(study_id: int, input_data: StudyUpdateRequest, user: dict = Depends(require_user)):
    """Update study"""
    study = await db.get_study_by_id(study_id)
    if not study or study["userId"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    update_data = {}
    if input_data.title is not None:
        update_data["title"] = input_data.title
    if input_data.analysisResult is not None:
        update_data["analysisResult"] = input_data.analysisResult
    
    await db.update_study(study_id, update_data)
    return {"success": True}


@router.delete("/api/studies/{study_id}")
async def studies_delete(study_id: int, user: dict = Depends(require_user)):
    """Delete study"""
    study = await db.get_study_by_id(study_id)
    if not study or study["userId"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    await db.delete_study(study_id)
    return {"success": True}


@router.get("/api/studies/{study_id}/pdf")
async def studies_download_pdf(study_id: int, user: dict = Depends(require_user)):
    """Download study as PDF"""
    study = await db.get_study_by_id(study_id)
    if not study or study["userId"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    if not study.get("analysisResult"):
        raise HTTPException(status_code=400, detail="No analysis result available")
    
    images = await db.get_study_images(study_id)
    from datetime import datetime
    created_at = datetime.fromisoformat(study["createdAt"].replace("Z", "+00:00"))
    
    try:
        pdf_buffer = await generate_pdf(
            title=study["title"],
            study_type=study["studyType"],
            created_at=created_at,
            analysis_result=study["analysisResult"],
            image_url=images[0]["url"] if images else None,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    
    # Convert to base64
    import base64
    base64_pdf = base64.b64encode(pdf_buffer).decode('utf-8')
    return {"pdf": base64_pdf, "filename": f"{study['title']}.pdf"}


# Chat endpoints
class ChatGetMessagesInput(BaseModel):
    studyId: int


@router.get("/api/studies/{study_id}/messages")
async def studies_get_chat_messages(study_id: int, user: dict = Depends(require_user)):
    """Get chat messages for study"""
    study = await db.get_study_by_id(study_id)
    if not study or study["userId"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    messages = await db.get_chat_messages(study_id)
    # Файловое хранилище возвращает словари, используем JSONResponse для правильного Content-Length
    return JSONResponse(content=messages)


@router.post("/api/studies/{study_id}/messages")
async def studies_send_chat_message(study_id: int, input_data: ChatSendMessageInput, user: dict = Depends(require_user)):
    """Send chat message"""
    study = await db.get_study_by_id(study_id)
    if not study or study["userId"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Save user message
    await db.create_chat_message({
        "studyId": study_id,
        "role": "user",
        "content": input_data.message,
    })
    
    # Prepare context for AI
    study_type_labels = {
        "retinal_scan": "Сканирование сетчатки",
        "optic_nerve": "Анализ зрительного нерва",
        "macular_analysis": "Анализ макулярной области",
        "brain": "Головной мозг",
        "lungs": "Легкие",
        "bone": "Опорно-двигательный аппарат",
        "eye": "Органы зрения",
    }
    
    system_prompt = f"""Вы - опытный офтальмолог-консультант. Вы помогаете врачам разобраться в результатах исследований.

Текущее исследование:
Тип: {study_type_labels.get(study["studyType"], study["studyType"])}
Название: {study["title"]}

Результаты анализа:
{study.get("analysisResult") or "Анализ еще не завершен"}

Отвечайте профессионально, используя медицинскую терминологию. Предоставляйте конкретные и полезные рекомендации."""
    
    # Get chat history
    chat_history = await db.get_chat_messages(study_id)
    messages = [
        {"role": "system", "content": system_prompt},
        *[
            {"role": msg["role"], "content": msg["content"]}
            for msg in chat_history[-10:]
        ],
    ]
    
    try:
        # Call LLM
        from server._core.llm import invoke_llm
        result = await invoke_llm(messages=messages)
        ai_response = result.get("choices", [{}])[0].get("message", {}).get("content")
        
        if not ai_response or not isinstance(ai_response, str):
            raise ValueError("No response from AI")
        
        # Save AI response
        await db.create_chat_message({
            "studyId": study_id,
            "role": "assistant",
            "content": ai_response,
        })
        
        return {"success": True, "message": ai_response}
    except Exception as error:
        print(f"Error in chat: {type(error).__name__}")
        raise HTTPException(status_code=500, detail="Failed to get AI response")

