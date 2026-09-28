from collections.abc import AsyncIterator

from asyncpg import PostgresError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"timeout": 2},
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def database_status() -> str:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return "connected"
    except (OSError, PostgresError, SQLAlchemyError):
        return "unavailable"
