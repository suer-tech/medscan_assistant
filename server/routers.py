"""Main API routers"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
# Убрали импорты моделей - теперь используем файловое хранилище
from server._core.dependencies import get_current_user, require_user
from server._core.cookies import get_session_cookie_options
from server._core.const import COOKIE_NAME, ONE_YEAR_MS
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


# Pydantic models for requests/responses
class StudyCreateInput(BaseModel):
    title: str = Field(..., min_length=1)
    studyType: str = Field(..., pattern="^(retinal_scan|optic_nerve|macular_analysis|free_query|template_form|ultrasound_thyroid|ultrasound_liver|lab_blood)$")


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
    filename: str
    mimeType: str


class StudyUploadImageOutput(BaseModel):
    id: int
    url: str


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
    password = login_data.password.strip()
    
    print(f"[Auth] Login attempt for email: '{email}'")
    
    # Simple authentication (no database for MVP)
    from server._core.simple_auth import (
        verify_simple_password,
        get_simple_user,
        create_session_for_user
    )
    
    # Verify password
    print(f"[Auth] Verifying password for email: '{email}'")
    
    if not verify_simple_password(email, password):
        print(f"[Auth] Password verification failed for email: '{email}'")
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
    
    print(f"[Auth] Cookie set: {COOKIE_NAME}={session_token[:20]}...")
    print(f"[Auth] Cookie options: {cookie_options}")
    
    # Проверяем, что cookie действительно установлен в заголовках
    set_cookie_header = response_obj.headers.get("set-cookie")
    print(f"[Auth] Set-Cookie header: {set_cookie_header}")
    print(f"[Auth] All response headers: {list(response_obj.headers.keys())}")
    
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
    result["images"] = images
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
    
    # Для MVP используем data URL напрямую (base64)
    # В production можно сохранять файлы локально или в S3
    image_url = input_data.imageData  # Используем base64 data URL напрямую
    
    # Save metadata to file storage
    image_id = await db.create_study_image({
        "studyId": study_id,
        "fileKey": f"studies/{user['id']}/{study_id}/{generate()}-{input_data.filename}",
        "url": image_url,  # Используем data URL
        "filename": input_data.filename,
        "mimeType": input_data.mimeType,
        "fileSize": len(input_data.imageData),  # Примерный размер
    })
    
    return {"id": image_id, "url": image_url}


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
    study = await db.get_study_by_id(study_id)
    if not study or study["userId"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    images = await db.get_study_images(study_id)
    if len(images) == 0:
        raise HTTPException(status_code=400, detail="No images uploaded")
    
    # Update status to analyzing
    await db.update_study(study_id, {"status": "analyzing"})
    
    try:
        # Get user query or template if provided
        user_query = input_data.userQuery if input_data and input_data.userQuery else None
        template = input_data.template if input_data and input_data.template else None
        
        # Analyze the first image
        if template:
            # Convert Pydantic models to dicts
            template_dicts = [t.dict() if hasattr(t, 'dict') else t for t in template]
            analysis_result = await analyze_template_form(images[0]["url"], template_dicts)
        else:
            analysis_result = await analyze_xray_image(images[0]["url"], study["studyType"], user_query=user_query)
        
        # Update study with results
        await db.update_study(study_id, {
            "status": "completed",
            "analysisResult": analysis_result,
        })
        
        return {"success": True, "analysisResult": analysis_result}
    except Exception as error:
        # Log detailed error
        error_message = str(error)
        print(f"[Analyze] Error for study {study_id}: {error_message}")
        
        # Don't save error status if we already have a result (partial success)
        current_study = await db.get_study_by_id(study_id)
        if current_study and current_study.get("analysisResult"):
            # If result exists, keep it but mark as error
            await db.update_study(study_id, {"status": "error"})
        else:
            # No result yet, mark as error
            await db.update_study(study_id, {"status": "error"})
        
        # Return detailed error message
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to analyze image: {error_message}"
        )


class StudyUpdateRequest(BaseModel):
    id: int
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
    
    pdf_buffer = await generate_pdf(
        title=study["title"],
        study_type=study["studyType"],
        created_at=created_at,
        analysis_result=study["analysisResult"],
        image_url=images[0]["url"] if images else None,
    )
    
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
        print(f"Error in chat: {error}")
        raise HTTPException(status_code=500, detail="Failed to get AI response")

