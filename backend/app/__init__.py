"""
ScribeSnap Backend — Application Package Initializer
====================================================

What: Marks the `app` directory as a Python package.
Why:  Enables module imports like `from app.config import settings`.
Who:  Used implicitly by Python's import system and explicitly by Alembic, pytest, and uvicorn.

Architecture Note:
    This backend follows a clean layered architecture:
    
    ┌─────────────────────────────────────┐
    │           Routes (API Layer)        │  ← HTTP concerns only
    ├─────────────────────────────────────┤
    │         Services (Business Logic)   │  ← Orchestration, validation
    ├─────────────────────────────────────┤
    │       Models & Schemas (Data)       │  ← SQLAlchemy ORM + Pydantic
    ├─────────────────────────────────────┤
    │        Database (Persistence)       │  ← Async SQLAlchemy sessions
    └─────────────────────────────────────┘
    
    Why this separation:
    - Routes handle HTTP details (status codes, headers) but delegate logic to services
    - Services contain business rules and can be tested without HTTP
    - Models represent database structure; Schemas represent API contracts
    - Database layer manages connection lifecycle independently
    
    This makes each layer independently testable and replaceable.
"""

__version__ = "1.0.0"
