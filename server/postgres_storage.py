"""Persistent SQL storage with the async contract used by the REST routes.

Only medscan_* tables are owned by this module. SQLite files are supported for
isolated development/tests; Vercel and production require PostgreSQL.
"""
import asyncio
from datetime import datetime, timezone
import os
import threading
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, MetaData, String, Table, Text,
    create_engine, delete, event, insert, select, text, update,
)
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool


metadata = MetaData()
studies = Table(
    "medscan_studies", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("userId", Integer, nullable=False, index=True),
    Column("title", Text, nullable=False),
    Column("studyType", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("analysisResult", Text, nullable=True),
    Column("createdAt", DateTime(timezone=True), nullable=False),
    Column("updatedAt", DateTime(timezone=True), nullable=False),
    sqlite_autoincrement=True,
)
images = Table(
    "medscan_images", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("studyId", Integer, ForeignKey("medscan_studies.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("fileKey", Text, nullable=False),
    Column("url", Text, nullable=False),
    Column("filename", Text, nullable=False),
    Column("mimeType", String(128), nullable=False),
    Column("fileSize", Integer, nullable=False),
    Column("createdAt", DateTime(timezone=True), nullable=False),
    sqlite_autoincrement=True,
)
messages = Table(
    "medscan_messages", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("studyId", Integer, ForeignKey("medscan_studies.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("role", String(32), nullable=False),
    Column("content", Text, nullable=False),
    Column("createdAt", DateTime(timezone=True), nullable=False),
    sqlite_autoincrement=True,
)

_engine: Optional[Engine] = None
_engine_lock = threading.Lock()
_SCHEMA_LOCK_ID = 0x4D45445343414E


def _database_url() -> URL:
    value = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if not value:
        raise RuntimeError("DATABASE_URL or POSTGRES_URL is required")
    try:
        url = make_url(value)
    except (SQLAlchemyError, ValueError, TypeError):
        raise RuntimeError("Database URL is invalid") from None
    backend = url.get_backend_name()
    production = bool(os.getenv("VERCEL")) or os.getenv("NODE_ENV", "").lower() == "production"
    if backend in ("postgres", "postgresql"):
        return url.set(drivername="postgresql+psycopg")
    if production:
        raise RuntimeError("PostgreSQL is required in production")
    if backend != "sqlite":
        raise RuntimeError("Only PostgreSQL or development SQLite is supported")
    if not url.database or url.database == ":memory:":
        raise RuntimeError("Development SQLite requires a persistent file URL")
    return url.set(drivername="sqlite")


def _get_engine() -> Engine:
    global _engine
    # Recheck production restrictions even if a development engine was cached.
    url = _database_url()
    with _engine_lock:
        if _engine is not None:
            if _engine.url != url:
                raise RuntimeError("Database configuration changed; restart the process")
            return _engine
        connect_args = {"connect_timeout": 10} if url.get_backend_name() == "postgresql" else {
            "timeout": 15, "check_same_thread": False,
        }
        candidate = None
        try:
            candidate = create_engine(
                url, poolclass=NullPool, connect_args=connect_args,
                echo=False, hide_parameters=True,
            )
            if url.get_backend_name() == "sqlite":
                @event.listens_for(candidate, "connect")
                def enable_foreign_keys(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()
            with candidate.begin() as connection:
                if url.get_backend_name() == "postgresql":
                    # Serialize cold-start DDL across separate serverless workers.
                    connection.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": _SCHEMA_LOCK_ID})
                metadata.create_all(connection, checkfirst=True)
        except (SQLAlchemyError, ImportError):
            if candidate is not None:
                candidate.dispose()
            raise RuntimeError("Database initialization failed") from None
        _engine = candidate
        return _engine


def _serialize(row) -> Dict[str, Any]:
    result = dict(row)
    for key, value in result.items():
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            result[key] = value.astimezone(timezone.utc).isoformat()
    return result


async def _run(operation):
    def transact():
        try:
            with _get_engine().begin() as connection:
                return operation(connection)
        except SQLAlchemyError:
            # SQL/driver errors can contain bound patient data or connection info.
            raise RuntimeError("Database operation failed") from None
    return await asyncio.to_thread(transact)


async def health_check() -> Dict[str, Any]:
    def check(connection):
        connection.execute(select(1)).scalar_one()
        backend = connection.dialect.name
        return {"database": "postgres" if backend == "postgresql" else backend, "persistent": True}
    return await _run(check)


async def get_studies_by_user_id(user_id: int) -> List[Dict[str, Any]]:
    return await _run(lambda connection: [
        _serialize(row) for row in connection.execute(
            select(studies).where(studies.c.userId == user_id).order_by(studies.c.id)
        ).mappings()
    ])


async def get_study_by_id(study_id: int) -> Optional[Dict[str, Any]]:
    def get(connection):
        row = connection.execute(select(studies).where(studies.c.id == study_id)).mappings().first()
        return _serialize(row) if row is not None else None
    return await _run(get)


async def create_study(study_data: Dict[str, Any]) -> int:
    now = datetime.now(timezone.utc)
    values = {
        "userId": study_data["userId"], "title": study_data["title"],
        "studyType": study_data["studyType"], "status": study_data.get("status", "draft"),
        "analysisResult": None, "createdAt": now, "updatedAt": now,
    }
    return await _run(lambda connection: int(connection.execute(insert(studies).values(**values)).inserted_primary_key[0]))


async def update_study(study_id: int, update_data: Dict[str, Any]) -> None:
    allowed = {"title", "studyType", "status", "analysisResult"}
    if set(update_data) - allowed:
        raise ValueError("Unsupported study update fields")
    values = {**update_data, "updatedAt": datetime.now(timezone.utc)}
    def change(connection):
        result = connection.execute(update(studies).where(studies.c.id == study_id).values(**values))
        if result.rowcount != 1:
            raise ValueError(f"Study with id {study_id} not found")
    await _run(change)


async def delete_study(study_id: int) -> None:
    # Both child tables have database-enforced ON DELETE CASCADE.
    await _run(lambda connection: connection.execute(delete(studies).where(studies.c.id == study_id)))


async def get_study_images(study_id: int) -> List[Dict[str, Any]]:
    return await _run(lambda connection: [
        _serialize(row) for row in connection.execute(
            select(images).where(images.c.studyId == study_id).order_by(images.c.id)
        ).mappings()
    ])


async def create_study_image(image_data: Dict[str, Any]) -> int:
    values = {key: image_data[key] for key in ("studyId", "fileKey", "url", "filename", "mimeType", "fileSize")}
    values["createdAt"] = datetime.now(timezone.utc)
    return await _run(lambda connection: int(connection.execute(insert(images).values(**values)).inserted_primary_key[0]))


async def get_chat_messages(study_id: int) -> List[Dict[str, Any]]:
    return await _run(lambda connection: [
        _serialize(row) for row in connection.execute(
            select(messages).where(messages.c.studyId == study_id).order_by(messages.c.createdAt, messages.c.id)
        ).mappings()
    ])


async def create_chat_message(message_data: Dict[str, Any]) -> int:
    values = {key: message_data[key] for key in ("studyId", "role", "content")}
    values["createdAt"] = datetime.now(timezone.utc)
    return await _run(lambda connection: int(connection.execute(insert(messages).values(**values)).inserted_primary_key[0]))
