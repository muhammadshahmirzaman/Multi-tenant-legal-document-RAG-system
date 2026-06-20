import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import asyncio
from contextlib import asynccontextmanager

engine = create_async_engine(settings.POSTGRES_URL, connect_args={"ssl": False}, future=True, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

@asynccontextmanager
async def get_db():
    """Async contextmanager suitable for scripts: `async with get_db() as db:`"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    # Create tables using metadata.create_all
    from app.db import models
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

async def close_db():
    await engine.dispose()

async def run_migrations():
    # Placeholder: run Alembic migrations if configured. For now ensure tables exist.
    await init_db()
