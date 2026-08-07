from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

_engine = None
_session_factory = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency helper that yields a transactional session context.
    Ensures rollback in case of exceptions and auto-closes session resource.
    """
    if _session_factory is None:
        raise RuntimeError(
            "Database connection has not been initialized. Call initialize_db first."
        )

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def initialize_db(database_url: str) -> None:
    """
    Initializes global connection pooling and session makers.
    Called once during application startup.
    """
    global _engine, _session_factory

    # Configure connection pool based on dialect
    if "sqlite" in database_url:
        # SQLite doesn't support pool_size/max_overflow, and needs check_same_thread=False
        _engine = create_async_engine(database_url, connect_args={"check_same_thread": False})
    else:
        # PostgreSQL configurations
        _engine = create_async_engine(
            database_url, pool_size=20, max_overflow=10, pool_pre_ping=True
        )

    _session_factory = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables() -> None:
    """
    Helper to automatically generate tables for declarative Base metadata.
    """
    global _engine
    if _engine is None:
        raise RuntimeError("Database connection has not been initialized.")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Safely disposes of active engine connections.
    """
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    _session_factory = None
