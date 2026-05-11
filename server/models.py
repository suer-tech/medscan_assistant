"""SQLAlchemy models for database tables"""
from datetime import datetime
from typing import Optional
import enum

# Optional SQLAlchemy imports - only if available
try:
    from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, ForeignKey
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import relationship
    Base = declarative_base()
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    # SQLAlchemy not available - create dummy classes
    SQLALCHEMY_AVAILABLE = False
    Base = None
    Column = None
    Integer = None
    String = None
    Text = None
    Enum = None
    DateTime = None
    ForeignKey = None
    relationship = None


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class StudyType(str, enum.Enum):
    RETINAL_SCAN = "retinal_scan"
    OPTIC_NERVE = "optic_nerve"
    MACULAR_ANALYSIS = "macular_analysis"


class StudyStatus(str, enum.Enum):
    DRAFT = "draft"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    ERROR = "error"


class ChatMessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


if SQLALCHEMY_AVAILABLE:
    class User(Base):
        __tablename__ = "users"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        openId = Column(String(64), unique=True, nullable=False, name="openId")
        name = Column(Text, nullable=True)
        email = Column(String(320), nullable=True, unique=True)
        passwordHash = Column(String(255), nullable=True, name="passwordHash")
        loginMethod = Column(String(64), nullable=True, name="loginMethod")
        role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
        createdAt = Column(DateTime, default=datetime.utcnow, nullable=False, name="createdAt")
        updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, name="updatedAt")
        lastSignedIn = Column(DateTime, default=datetime.utcnow, nullable=False, name="lastSignedIn")
        
        # Relationships
        studies = relationship("Study", back_populates="user")


    class Study(Base):
        __tablename__ = "studies"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        userId = Column(Integer, ForeignKey("users.id"), nullable=False, name="userId")
        title = Column(String(255), nullable=False)
        studyType = Column(Enum(StudyType), nullable=False, name="studyType")
        status = Column(Enum(StudyStatus), default=StudyStatus.DRAFT, nullable=False)
        analysisResult = Column(Text, nullable=True, name="analysisResult")
        createdAt = Column(DateTime, default=datetime.utcnow, nullable=False, name="createdAt")
        updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, name="updatedAt")
        
        # Relationships
        user = relationship("User", back_populates="studies")
        images = relationship("StudyImage", back_populates="study", cascade="all, delete-orphan")
        chat_messages = relationship("ChatMessage", back_populates="study", cascade="all, delete-orphan")


    class StudyImage(Base):
        __tablename__ = "studyImages"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        studyId = Column(Integer, ForeignKey("studies.id"), nullable=False, name="studyId")
        fileKey = Column(String(512), nullable=False, name="fileKey")
        url = Column(Text, nullable=False)
        filename = Column(String(255), nullable=False)
        mimeType = Column(String(100), nullable=False, name="mimeType")
        fileSize = Column(Integer, nullable=False, name="fileSize")
        createdAt = Column(DateTime, default=datetime.utcnow, nullable=False, name="createdAt")
        
        # Relationships
        study = relationship("Study", back_populates="images")


    class ChatMessage(Base):
        __tablename__ = "chatMessages"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        studyId = Column(Integer, ForeignKey("studies.id"), nullable=False, name="studyId")
        role = Column(Enum(ChatMessageRole), nullable=False)
        content = Column(Text, nullable=False)
        createdAt = Column(DateTime, default=datetime.utcnow, nullable=False, name="createdAt")
        
        # Relationships
        study = relationship("Study", back_populates="chat_messages")
else:
    # Dummy classes when SQLAlchemy is not available
    class User:
        pass
    
    class Study:
        pass
    
    class StudyImage:
        pass
    
    class ChatMessage:
        pass

