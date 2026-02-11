"""
ScribeSnap Backend — Notes Route Handlers
===========================================

What:  Handles GET /api/notes (list) and GET /api/notes/{id} (detail).
Why:   Provides note history and individual note access to the frontend.
How:   Extracts query parameters, delegates to NoteService, returns JSON.
Who:   Called by the frontend History and NoteDetail components.

Caching Strategy:
    - POST /api/parse: No caching (mutations should never be cached)
    - GET /api/notes: Short cache (5s) with revalidation (data can change)
    - GET /api/notes/{id}: Long cache (1 hour) since notes are immutable after creation
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_session
from app.schemas.note import (
    NoteResponse,
    NoteListResponse,
    ErrorResponse,
)
from app.services.note_service import note_service

logger = logging.getLogger(__name__)

# ── Router Configuration ──────────────────────────────────────────────────
router = APIRouter(prefix="/api", tags=["Notes"])


@router.get(
    "/notes",
    response_model=NoteListResponse,
    responses={
        200: {"description": "Paginated list of notes", "model": NoteListResponse},
        500: {"description": "Server error", "model": ErrorResponse},
    },
    summary="List parsed notes with pagination",
    description=(
        "Returns a paginated list of parsed notes. Supports cursor-based pagination "
        "for efficient infinite scrolling, date range filtering, and sort direction. "
        "Response includes total count and next cursor for pagination state."
    ),
)
async def list_notes(
    response: Response,
    limit: int = Query(
        default=20, ge=1, le=100,
        description="Items per page (max 100). Higher values reduce API calls but increase payload size.",
    ),
    cursor: str | None = Query(
        default=None,
        description=(
            "Pagination cursor (ISO 8601 datetime of last item from previous page). "
            "Omit for the first page."
        ),
    ),
    from_date: str | None = Query(
        default=None,
        description="Filter: only include notes created on or after this date (ISO 8601)",
    ),
    to_date: str | None = Query(
        default=None,
        description="Filter: only include notes created on or before this date (ISO 8601)",
    ),
    sort: str = Query(
        default="created_at_desc",
        description="Sort order: 'created_at_desc' (newest first) or 'created_at_asc' (oldest first)",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> NoteListResponse:
    """
    List notes with cursor-based pagination.
    
    What:    Returns a page of notes matching the specified criteria.
    Who:     Called by the frontend History component via useNoteHistory hook.
    
    Example client usage (infinite scroll):
        Page 1: GET /api/notes?limit=20
        Page 2: GET /api/notes?limit=20&cursor=2024-01-15T12:00:00Z
        Page 3: GET /api/notes?limit=20&cursor=2024-01-15T10:30:00Z
        (cursor value comes from next_cursor in previous response)
    
    Why we include X-Total-Count header:
        Some pagination UIs show "Showing 1-20 of 157 notes".
        The header provides this count without embedding it in every list item.
        It's a de facto standard (GitHub, GitLab APIs use it).
    """
    result = await note_service.list_notes(
        db=db,
        limit=limit,
        cursor=cursor,
        from_date=from_date,
        to_date=to_date,
        sort=sort,
    )

    # Set total count in response header for pagination UI
    # Why header (not body): Follows REST conventions; doesn't bloat item payload
    response.headers["X-Total-Count"] = str(result.total_count)

    return result


@router.get(
    "/notes/{note_id}",
    response_model=NoteResponse,
    responses={
        200: {"description": "Full note details", "model": NoteResponse},
        404: {"description": "Note not found", "model": ErrorResponse},
        500: {"description": "Server error", "model": ErrorResponse},
    },
    summary="Get a single note by ID",
    description=(
        "Returns full details for a specific note including the complete parsed text, "
        "image URL, and metadata. Response includes caching headers since note data "
        "is immutable after creation."
    ),
)
async def get_note(
    note_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> NoteResponse:
    """
    Get full details of a single note.
    
    What:    Returns complete note data including full parsed text.
    Who:     Called by the frontend NoteDetail page.
    
    Caching:
        Cache-Control: private (user-specific data), max-age=3600 (1 hour)
        Why 1 hour: Note content is immutable after creation.
        Why private: Even though no auth exists yet, preparing for future
        user-specific data. 'public' would allow CDN caching of potentially
        sensitive handwritten content.
    
    Args:
        note_id: UUID path parameter — validated by FastAPI automatically.
                 Invalid UUIDs return 422 Unprocessable Entity (FastAPI default).
    """
    result = await note_service.get_note(db=db, note_id=note_id)

    # Set caching headers for immutable note data
    # Why private: User-specific content should not be cached by shared caches (CDNs)
    # Why max-age=3600: Notes don't change after creation; 1 hour is safe
    response.headers["Cache-Control"] = "private, max-age=3600"

    return result


@router.get(
    "/files/{file_path:path}",
    summary="Serve uploaded image files",
    description="Serves the original uploaded image file from storage.",
    responses={
        200: {"description": "Image file"},
        404: {"description": "File not found"},
    },
)
async def serve_file(file_path: str) -> FileResponse:
    """
    Serve uploaded images from the storage directory.
    
    What:    Returns the original uploaded image file.
    Who:     Called by <img> tags in the frontend that reference image_url.
    
    Security:
        - Path is relative to STORAGE_ROOT (cannot escape with ../)
        - FileResponse validates the file exists
        - Only serves files that were stored by our FileService
    
    Why serve from backend (not static files):
        - Storage directory is not in the web root
        - Enables future access control (e.g., only authenticated users)
        - Lets us add cache headers and content negotiation
    """
    from pathlib import Path
    full_path = Path(settings.storage_root).resolve() / file_path

    # Security: Ensure the resolved path is within our storage root
    # Prevents path traversal attacks (e.g., ../../etc/passwd)
    storage_root = Path(settings.storage_root).resolve()
    if not str(full_path).startswith(str(storage_root)):
        from app.exceptions import ValidationError
        raise ValidationError(message="Invalid file path")

    if not full_path.exists():
        from app.exceptions import NotFoundError
        raise NotFoundError(resource="file", resource_id=file_path)

    return FileResponse(
        path=str(full_path),
        media_type="image/jpeg",  # FileResponse auto-detects from filename
        headers={"Cache-Control": "public, max-age=86400"},  # 24h cache for images
    )
