"""Database operations using SQLAlchemy"""
from typing import Optional, List
from server._core.env import env

# Optional SQLAlchemy imports - only if available
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.exc import SQLAlchemyError
    from server.models import (
        Base, User, Study, StudyImage, ChatMessage,
        UserRole, StudyType, StudyStatus, ChatMessageRole
    )
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    # SQLAlchemy not available
    SQLALCHEMY_AVAILABLE = False
    create_engine = None
    sessionmaker = None
    Session = None
    SQLAlchemyError = None
    Base = None
    User = None
    Study = None
    StudyImage = None
    ChatMessage = None
    UserRole = None
    StudyType = None
    StudyStatus = None
    ChatMessageRole = None

_engine = None
_SessionLocal = None
_db: Optional[Session] = None


def get_db() -> Optional[Session]:
    """Get database session, creating connection if needed"""
    global _engine, _SessionLocal, _db
    
    if not SQLALCHEMY_AVAILABLE:
        return None
    
    if not env.database_url:
        return None
    
    if _engine is None:
        try:
            _engine = create_engine(
                env.database_url,
                pool_pre_ping=True,
                echo=False
            )
            _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        except Exception as error:
            print(f"[Database] Failed to connect: {error}")
            return None
    
    if _SessionLocal is None:
        return None
    
    return _SessionLocal()


async def upsert_user(user_data: dict) -> None:
    """Insert or update user"""
    if not SQLALCHEMY_AVAILABLE:
        print("[Database] Cannot upsert user: SQLAlchemy not available")
        return
    
    if not user_data.get("openId"):
        raise ValueError("User openId is required for upsert")
    
    db = get_db()
    if not db:
        print("[Database] Cannot upsert user: database not available")
        return
    
    try:
        existing_user = db.query(User).filter(User.openId == user_data["openId"]).first()
        
        if existing_user:
            # Update existing user
            for key, value in user_data.items():
                if key != "openId" and key != "password" and value is not None:
                    setattr(existing_user, key, value)
            
            # Handle password separately (hash it)
            if "password" in user_data and user_data["password"]:
                from server._core.password import hash_password
                existing_user.passwordHash = hash_password(user_data["password"])
            
            # Set role to admin if owner
            if user_data["openId"] == env.owner_open_id:
                existing_user.role = UserRole.ADMIN
            
            if not existing_user.lastSignedIn:
                from datetime import datetime
                existing_user.lastSignedIn = datetime.utcnow()
        else:
            # Create new user
            role = UserRole.ADMIN if user_data["openId"] == env.owner_open_id else UserRole.USER
            
            # Hash password if provided
            password_hash = None
            if "password" in user_data and user_data["password"]:
                from server._core.password import hash_password
                password_hash = hash_password(user_data["password"])
            
            new_user = User(
                openId=user_data["openId"],
                name=user_data.get("name"),
                email=user_data.get("email"),
                passwordHash=password_hash,
                loginMethod=user_data.get("loginMethod"),
                role=role,
            )
            db.add(new_user)
        
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        print(f"[Database] Failed to upsert user: {error}")
        raise
    finally:
        db.close()


async def get_user_by_open_id(open_id: str) -> Optional[User]:
    """Get user by openId"""
    if not SQLALCHEMY_AVAILABLE:
        print("[Database] Cannot get user: SQLAlchemy not available")
        return None
    
    db = get_db()
    if not db:
        print("[Database] Cannot get user: database not available")
        return None
    
    try:
        user = db.query(User).filter(User.openId == open_id).first()
        return user
    except SQLAlchemyError as error:
        print(f"[Database] Failed to get user: {error}")
        return None
    finally:
        db.close()


async def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email"""
    if not SQLALCHEMY_AVAILABLE:
        print("[Database] Cannot get user: SQLAlchemy not available")
        return None
    
    db = get_db()
    if not db:
        print("[Database] Cannot get user: database not available")
        return None
    
    try:
        user = db.query(User).filter(User.email == email).first()
        return user
    except SQLAlchemyError as error:
        print(f"[Database] Failed to get user by email: {error}")
        return None
    finally:
        db.close()


# Study operations
async def create_study(study_data: dict) -> int:
    """Create a new study and return its ID"""
    if not SQLALCHEMY_AVAILABLE:
        raise ValueError("SQLAlchemy not available")
    
    db = get_db()
    if not db:
        raise ValueError("Database not available")
    
    try:
        study = Study(
            userId=study_data["userId"],
            title=study_data["title"],
            studyType=StudyType(study_data["studyType"]),
            status=StudyStatus(study_data.get("status", "draft")),
        )
        db.add(study)
        db.commit()
        db.refresh(study)
        return study.id
    except SQLAlchemyError as error:
        db.rollback()
        print(f"[Database] Failed to create study: {error}")
        raise
    finally:
        db.close()


async def get_studies_by_user_id(user_id: int) -> List[Study]:
    """Get all studies for a user"""
    if not SQLALCHEMY_AVAILABLE:
        return []
    
    db = get_db()
    if not db:
        return []
    
    try:
        studies = db.query(Study).filter(Study.userId == user_id).all()
        return studies
    except SQLAlchemyError as error:
        print(f"[Database] Failed to get studies: {error}")
        return []
    finally:
        db.close()


async def get_study_by_id(study_id: int) -> Optional[Study]:
    """Get study by ID"""
    if not SQLALCHEMY_AVAILABLE:
        return None
    
    db = get_db()
    if not db:
        return None
    
    try:
        study = db.query(Study).filter(Study.id == study_id).first()
        return study
    except SQLAlchemyError as error:
        print(f"[Database] Failed to get study: {error}")
        return None
    finally:
        db.close()


async def update_study(study_id: int, data: dict) -> None:
    """Update study"""
    if not SQLALCHEMY_AVAILABLE:
        raise ValueError("SQLAlchemy not available")
    
    db = get_db()
    if not db:
        raise ValueError("Database not available")
    
    try:
        study = db.query(Study).filter(Study.id == study_id).first()
        if not study:
            raise ValueError(f"Study {study_id} not found")
        
        for key, value in data.items():
            if hasattr(study, key) and value is not None:
                if key == "studyType":
                    setattr(study, key, StudyType(value))
                elif key == "status":
                    setattr(study, key, StudyStatus(value))
                else:
                    setattr(study, key, value)
        
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        print(f"[Database] Failed to update study: {error}")
        raise
    finally:
        db.close()


async def delete_study(study_id: int) -> None:
    """Delete study"""
    if not SQLALCHEMY_AVAILABLE:
        raise ValueError("SQLAlchemy not available")
    
    db = get_db()
    if not db:
        raise ValueError("Database not available")
    
    try:
        study = db.query(Study).filter(Study.id == study_id).first()
        if study:
            db.delete(study)
            db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        print(f"[Database] Failed to delete study: {error}")
        raise
    finally:
        db.close()


# Study image operations
async def create_study_image(image_data: dict) -> int:
    """Create study image and return its ID"""
    if not SQLALCHEMY_AVAILABLE:
        raise ValueError("SQLAlchemy not available")
    
    db = get_db()
    if not db:
        raise ValueError("Database not available")
    
    try:
        image = StudyImage(
            studyId=image_data["studyId"],
            fileKey=image_data["fileKey"],
            url=image_data["url"],
            filename=image_data["filename"],
            mimeType=image_data["mimeType"],
            fileSize=image_data["fileSize"],
        )
        db.add(image)
        db.commit()
        db.refresh(image)
        return image.id
    except SQLAlchemyError as error:
        db.rollback()
        print(f"[Database] Failed to create study image: {error}")
        raise
    finally:
        db.close()


async def get_study_images(study_id: int) -> List[StudyImage]:
    """Get all images for a study"""
    if not SQLALCHEMY_AVAILABLE:
        return []
    
    db = get_db()
    if not db:
        return []
    
    try:
        images = db.query(StudyImage).filter(StudyImage.studyId == study_id).all()
        return images
    except SQLAlchemyError as error:
        print(f"[Database] Failed to get study images: {error}")
        return []
    finally:
        db.close()


# Chat message operations
async def create_chat_message(message_data: dict) -> int:
    """Create chat message and return its ID"""
    if not SQLALCHEMY_AVAILABLE:
        raise ValueError("SQLAlchemy not available")
    
    db = get_db()
    if not db:
        raise ValueError("Database not available")
    
    try:
        message = ChatMessage(
            studyId=message_data["studyId"],
            role=ChatMessageRole(message_data["role"]),
            content=message_data["content"],
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message.id
    except SQLAlchemyError as error:
        db.rollback()
        print(f"[Database] Failed to create chat message: {error}")
        raise
    finally:
        db.close()


async def get_chat_messages(study_id: int) -> List[ChatMessage]:
    """Get all chat messages for a study"""
    if not SQLALCHEMY_AVAILABLE:
        return []
    
    db = get_db()
    if not db:
        return []
    
    try:
        messages = db.query(ChatMessage).filter(ChatMessage.studyId == study_id).all()
        return messages
    except SQLAlchemyError as error:
        print(f"[Database] Failed to get chat messages: {error}")
        return []
    finally:
        db.close()

