"""
hermes-core/db/session.py — Engine async + sessionmaker SQLAlchemy 2.x.

Pattern recommandé :
  - engine global partagé (pool de connexions)
  - async_sessionmaker pour créer des sessions par requête
  - Base déclarative pour les modèles
  - get_db() dependency pour FastAPI
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import settings


class Base(DeclarativeBase):
    """Base déclarative SQLAlchemy 2.x pour tous les modèles."""
    pass


# Engine global — pool partagé entre requêtes
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=settings.db_pool_pre_ping,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency FastAPI : fournit une session DB par requête."""
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Context manager pour usage hors FastAPI (scripts, tasks)."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise