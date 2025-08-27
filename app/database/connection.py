"""Database connection and setup"""

import asyncio
from typing import AsyncGenerator
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.utils.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# SQLAlchemy base
Base = declarative_base()

# Database engine and session factory
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=20
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create database tables"""
    async with engine.begin() as conn:
        # Import models to register them with Base
        from .models import Order, Payment, Event
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def check_database_connection() -> bool:
    """Check if database connection is working"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        return False
