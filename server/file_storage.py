"""Простое файловое хранилище для MVP - JSON файлы на диске"""
import json
import os
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

# Директория для хранения данных
STORAGE_DIR = Path(__file__).parent.parent / "data"
STORAGE_DIR.mkdir(exist_ok=True)

STUDIES_FILE = STORAGE_DIR / "studies.json"
IMAGES_FILE = STORAGE_DIR / "images.json"
MESSAGES_FILE = STORAGE_DIR / "messages.json"

# Инициализация файлов, если их нет
def _init_files():
    """Инициализировать файлы хранилища, если их нет"""
    if not STUDIES_FILE.exists():
        with open(STUDIES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    if not IMAGES_FILE.exists():
        with open(IMAGES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    if not MESSAGES_FILE.exists():
        with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

_init_files()


def _load_studies() -> List[Dict[str, Any]]:
    """Загрузить все исследования из файла"""
    try:
        with open(STUDIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_studies(studies: List[Dict[str, Any]]):
    """Сохранить исследования в файл"""
    with open(STUDIES_FILE, "w", encoding="utf-8") as f:
        json.dump(studies, f, indent=2, ensure_ascii=False, default=str)


def _load_images() -> List[Dict[str, Any]]:
    """Загрузить все изображения из файла"""
    try:
        with open(IMAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_images(images: List[Dict[str, Any]]):
    """Сохранить изображения в файл"""
    with open(IMAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(images, f, indent=2, ensure_ascii=False, default=str)


def _load_messages() -> List[Dict[str, Any]]:
    """Загрузить все сообщения из файла"""
    try:
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_messages(messages: List[Dict[str, Any]]):
    """Сохранить сообщения в файл"""
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False, default=str)


# Study operations
async def get_studies_by_user_id(user_id: int) -> List[Dict[str, Any]]:
    """Получить все исследования пользователя"""
    studies = _load_studies()
    return [s for s in studies if s.get("userId") == user_id]


async def get_study_by_id(study_id: int) -> Optional[Dict[str, Any]]:
    """Получить исследование по ID"""
    studies = _load_studies()
    for study in studies:
        if study.get("id") == study_id:
            return study
    return None


async def create_study(study_data: Dict[str, Any]) -> int:
    """Создать новое исследование"""
    studies = _load_studies()
    
    # Найти максимальный ID
    max_id = max([s.get("id", 0) for s in studies], default=0)
    new_id = max_id + 1
    
    now = datetime.utcnow().isoformat()
    new_study = {
        "id": new_id,
        "userId": study_data["userId"],
        "title": study_data["title"],
        "studyType": study_data["studyType"],
        "status": study_data.get("status", "draft"),
        "analysisResult": None,
        "createdAt": now,
        "updatedAt": now,
    }
    
    studies.append(new_study)
    _save_studies(studies)
    
    print(f"[FileStorage] Study created: id={new_id}, title={study_data['title']}")
    return new_id


async def update_study(study_id: int, update_data: Dict[str, Any]) -> None:
    """Обновить исследование"""
    studies = _load_studies()
    
    for study in studies:
        if study.get("id") == study_id:
            study.update(update_data)
            study["updatedAt"] = datetime.utcnow().isoformat()
            _save_studies(studies)
            print(f"[FileStorage] Study updated: id={study_id}")
            return
    
    raise ValueError(f"Study with id {study_id} not found")


async def delete_study(study_id: int) -> None:
    """Удалить исследование"""
    studies = _load_studies()
    images = _load_images()
    messages = _load_messages()
    
    # Удалить исследование
    studies = [s for s in studies if s.get("id") != study_id]
    _save_studies(studies)
    
    # Удалить связанные изображения
    images = [img for img in images if img.get("studyId") != study_id]
    _save_images(images)
    
    # Удалить связанные сообщения
    messages = [msg for msg in messages if msg.get("studyId") != study_id]
    _save_messages(messages)
    
    print(f"[FileStorage] Study deleted: id={study_id}")


# Image operations
async def get_study_images(study_id: int) -> List[Dict[str, Any]]:
    """Получить изображения исследования"""
    images = _load_images()
    return [img for img in images if img.get("studyId") == study_id]


async def create_study_image(image_data: Dict[str, Any]) -> int:
    """Создать запись об изображении"""
    images = _load_images()
    
    # Найти максимальный ID
    max_id = max([img.get("id", 0) for img in images], default=0)
    new_id = max_id + 1
    
    now = datetime.utcnow().isoformat()
    new_image = {
        "id": new_id,
        "studyId": image_data["studyId"],
        "fileKey": image_data["fileKey"],
        "url": image_data["url"],
        "filename": image_data["filename"],
        "mimeType": image_data["mimeType"],
        "fileSize": image_data["fileSize"],
        "createdAt": now,
    }
    
    images.append(new_image)
    _save_images(images)
    
    print(f"[FileStorage] Image created: id={new_id}, studyId={image_data['studyId']}")
    return new_id


# Message operations
async def get_chat_messages(study_id: int) -> List[Dict[str, Any]]:
    """Получить сообщения чата исследования"""
    messages = _load_messages()
    study_messages = [msg for msg in messages if msg.get("studyId") == study_id]
    # Сортировать по дате создания
    study_messages.sort(key=lambda x: x.get("createdAt", ""))
    return study_messages


async def create_chat_message(message_data: Dict[str, Any]) -> int:
    """Создать сообщение чата"""
    messages = _load_messages()
    
    # Найти максимальный ID
    max_id = max([msg.get("id", 0) for msg in messages], default=0)
    new_id = max_id + 1
    
    now = datetime.utcnow().isoformat()
    new_message = {
        "id": new_id,
        "studyId": message_data["studyId"],
        "role": message_data["role"],
        "content": message_data["content"],
        "createdAt": now,
    }
    
    messages.append(new_message)
    _save_messages(messages)
    
    print(f"[FileStorage] Message created: id={new_id}, studyId={message_data['studyId']}")
    return new_id

