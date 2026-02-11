"""
ScribeSnap Backend — Database Session Management
==================================================

What:  Async SQLAlchemy engine, session factory, and FastAPI dependency.
Why:   Centralizes all database connection logic in one place.
How:   Creates an async engine with connection pooling, provides a session
       dependency that auto-commits on success and auto-rolls-back on error.
Who:   Used by route handlers via FastAPI's dependency injection system.
When:  Engine is created at module import; sessions are created per-request.

Architecture Decision:
    We use async SQLAlchemy (with asyncpg driver) because:
    1. Non-blocking I/O — a slow query doesn't block other requests
    2. Better resource utilization under concurrent load
    3. Natural fit with FastAPI's async request handling
    Alternative considered: Synchronous SQLAlchemy — simpler but blocks the event loop

Connection Pooling Strategy:
    pool_size=20:     Persistent connections for normal load
    max_overflow=10:  Temporary connections for traffic spikes (total max = 30)
    pool_pre_ping:    Validates connections before use (catches stale connections)
    pool_recycle=3600: Recycles connections every hour (prevents long-lived stale connections)
    
    Why these values:
    - PostgreSQL default max_connections = 100
    - With pool_size=20 and max_overflow=10, we use at most 30 connections
    - This leaves headroom for direct DB access, migrations, and monitoring
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ── Engine Configuration ──────────────────────────────────────────────────
# What: The async engine manages the connection pool and executes SQL
# Why create_async_engine: Enables non-blocking database operations
engine = create_async_engine(
    settings.database_url,
    # Pool Configuration — controls how connections are managed
    pool_size=settings.db_pool_size,          # Persistent connections (default: 20)
    max_overflow=settings.db_max_overflow,     # Extra connections for spikes (default: 10)
    pool_pre_ping=settings.db_pool_pre_ping,  # Validate before use (default: True)
    pool_recycle=3600,                         # Recycle after 1 hour to prevent stale connections

    # Echo SQL queries in DEBUG mode for development visibility
    # Why conditional: SQL logging is noisy; only useful during development
    echo=settings.log_level == "DEBUG",
)

# ── Session Factory ───────────────────────────────────────────────────────
# What: Creates new AsyncSession instances with consistent configuration
# Why factory pattern: Each request gets its own session (isolation)
# expire_on_commit=False: Prevents lazy-loading issues after commit
#   Without this, accessing attributes after commit triggers a new DB query,
#   which fails outside the session context
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base Model ────────────────────────────────────────────────────────────
# What: Base class for all SQLAlchemy models
# Why DeclarativeBase: SQLAlchemy 2.0+ pattern (replaces legacy declarative_base())
# How: All model classes inherit from this to get ORM mapping
class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    
    All models inherit from this class to:
    1. Register with SQLAlchemy's metadata (used by Alembic for migrations)
    2. Get common ORM functionality (querying, relationships, etc.)
    3. Share a single metadata object for consistent schema management
    """
    pass


# ── Session Dependency ────────────────────────────────────────────────────
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.
    
    What:    Creates an async session, yields it for use, and handles cleanup.
    Who:     Injected into route handlers via FastAPI's Depends() system.
    When:    Created at the start of each request, disposed at the end.
    
    How it works:
        1. Creates a new session from the factory
        2. Yields it to the route handler (the handler performs queries)
        3. On success: commits the transaction (saves changes)
        4. On error: rolls back the transaction (discards changes)
        5. Always: closes the session (returns connection to pool)
    
    Why this pattern:
        - Automatic rollback prevents partial writes on errors
        - Session-per-request ensures each request has isolated state
        - Connection is returned to pool even if the handler raises an exception
    
    Example usage in a route:
        @router.get("/notes")
        async def get_notes(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(Note))
            return result.scalars().all()
    
    Raises:
        Any database exceptions are propagated to the global error handler,
        which returns appropriate HTTP status codes.
    """
    async with async_session_factory() as session:
        try:
            yield session
            # If we reach here without exception, commit the transaction
            # Why explicit commit: Gives us control over when writes are persisted
            await session.commit()
        except Exception:
            # On any error, roll back to prevent partial/corrupt data
            # Why catch broad Exception: We want to rollback for ANY failure,
            # including non-DB errors (e.g., a bug in serialization after a query)
            await session.rollback()
            raise  # Re-raise so the global error handler can respond appropriately
        finally:
            # Always close the session to return the connection to the pool
            # Why finally: Ensures cleanup even if commit or rollback fails
            await session.close()


# ── Lifecycle Helpers ─────────────────────────────────────────────────────
async def dispose_engine() -> None:
    """
    What:  Gracefully closes all connections in the pool.
    When:  Called during application shutdown (lifespan handler).
    Why:   Prevents connection leaks and ensures clean PostgreSQL disconnection.
    How:   Disposes the engine, which closes all pooled connections.
    """
    await engine.dispose()
