"""
ScribeSnap Backend — Test Configuration (conftest.py)
======================================================

What:  Shared pytest fixtures for the entire test suite.
Why:   Provides reusable test infrastructure (mocked DB, API client, temp files).
How:   pytest auto-discovers conftest.py and makes fixtures available to all tests.
Who:   Used by all test files in the tests/ directory.
When:  Fixtures are created per-test or per-session as specified.

Fixture Hierarchy:
    Session-scoped (created once for all tests):
    └── event_loop: Shared asyncio event loop
    └── mock_settings: Patched application settings
    
    Function-scoped (created fresh for each test):
    ├── mock_db_session: Mock database session (no real DB needed)
    ├── temp_storage: Temporary directory for file operations
    ├── sample_image_bytes: Fake image content for upload tests
    └── test_client: HTTPX AsyncClient for API endpoint testing
"""

import os
import shutil
import tempfile
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.config import settings


# ══════════════════════════════════════════════════════════════════════════
# Environment Setup
# ══════════════════════════════════════════════════════════════════════════

# Override settings for testing BEFORE any app imports
# Why: Prevents tests from using production database or API keys
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["GEMINI_API_KEY"] = "test-key-not-real"
os.environ["STORAGE_ROOT"] = tempfile.mkdtemp(prefix="scribesnap_test_")
os.environ["LOG_LEVEL"] = "WARNING"  # Reduce noise during tests


# ══════════════════════════════════════════════════════════════════════════
# Session-Scoped Fixtures (created once for all tests)
# ══════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════
# Function-Scoped Fixtures (created fresh for each test)
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_db_session():
    """
    Provides a mock async database session.
    
    What:    A MagicMock that simulates AsyncSession behavior.
    Why:     Tests should not require a real database.
    How:     Mocks execute, flush, commit, rollback, and close methods.
    
    Usage:
        async def test_get_note(mock_db_session):
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = note
            result = await note_service.get_note(mock_db_session, note_id)
    """
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def temp_storage(tmp_path):
    """
    Provides a temporary directory for file storage tests.
    
    What:    A fresh temporary directory for each test.
    Why:     Isolates file operations between tests.
    How:     Uses pytest's tmp_path fixture (automatically cleaned up).
    """
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    return str(storage_dir)


@pytest.fixture
def sample_image_bytes():
    """
    Provides minimal valid JPEG bytes for upload tests.
    
    What:    A tiny but technically valid JPEG image.
    Why:     Tests need real image bytes for MIME type validation.
    How:     Minimal JPEG: SOI marker + JFIF header + EOI marker.
    
    Note: This is NOT a real photograph — it's the smallest valid JPEG.
    Gemini would reject it, but it passes MIME validation.
    """
    # Minimal JPEG: Start of Image (FFD8) + JFIF marker + End of Image (FFD9)
    return (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xd9'
    )


@pytest.fixture
def sample_note_data():
    """
    Provides a dictionary matching the Note model fields.
    
    What:    Test data for creating Note instances.
    Why:     Consistent test data across multiple test files.
    """
    return {
        "id": uuid4(),
        "image_path": "2024/01/15/test-uuid.jpg",
        "parsed_text": "This is a sample parsed text from a handwritten note.",
        "created_at": datetime.now(timezone.utc),
        "status": "completed",
        "error_message": None,
        "retry_count": 0,
    }


@pytest_asyncio.fixture
async def test_client():
    """
    Provides an async HTTP test client for endpoint testing.
    
    What:    HTTPX AsyncClient configured to talk to our FastAPI app.
    Why:     Enables testing of HTTP endpoints without running a server.
    How:     Uses ASGITransport to route requests directly to the app.
    
    Usage:
        async def test_health(test_client):
            response = await test_client.get("/health")
            assert response.status_code == 200
    """
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
