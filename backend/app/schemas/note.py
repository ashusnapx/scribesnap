"""
ScribeSnap Backend — Pydantic Request/Response Schemas
=======================================================

What:  Pydantic models defining the API contract between frontend and backend.
Why:   Strict input validation, automatic serialization, and OpenAPI doc generation.
How:   FastAPI uses these models to validate request bodies, serialize responses,
       and generate Swagger/OpenAPI documentation automatically.
Who:   Used by route handlers as return types and by the frontend as API contracts.
When:  Validated on every request (input) and serialized on every response (output).

Design Decision:
    Schemas are separate from SQLAlchemy models because:
    1. API contracts change independently of database schema (e.g., adding computed fields)
    2. We control exactly what data is exposed (security: never leak internal fields)
    3. Validation rules differ from DB constraints (e.g., API requires file metadata)
    4. OpenAPI docs are generated from schemas, not from DB models
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ══════════════════════════════════════════════════════════════════════════
# Response Models — What the API returns to clients
# ══════════════════════════════════════════════════════════════════════════


class NoteResponse(BaseModel):
    """
    What:  Full representation of a parsed note.
    Who:   Returned by GET /api/notes/{id} for individual note detail.
    When:  Client navigates to a specific note's detail page.
    
    Why these fields:
        - id: Client uses this for routing and future API calls
        - image_url: Frontend constructs <img> src from this
        - parsed_text: The main value — extracted handwritten text
        - created_at: Displayed as relative time ("2 hours ago")
        - status: Allows frontend to show processing state
        - error_message: Shown to user when parsing failed
    """
    id: uuid.UUID = Field(description="Unique note identifier (UUID)")
    image_url: str = Field(description="URL path to access the uploaded image")
    parsed_text: str = Field(description="Full text extracted from handwritten image")
    created_at: datetime = Field(description="When the note was created (UTC ISO 8601)")
    status: str = Field(description="Processing state: processing, completed, failed")
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if parsing failed (null on success)"
    )

    model_config = {"from_attributes": True}


class NoteListItem(BaseModel):
    """
    What:  Compact note representation for list/grid views.
    Who:   Returned by GET /api/notes as array items.
    Why:   Smaller payload than NoteResponse — includes text preview (first 200 chars)
           instead of full text. Reduces bandwidth for pages showing many notes.
    
    Preview truncation:
        Why 200 chars: Balances readability with bandwidth. A card in the grid
        typically shows 2-3 lines of text, which is ~150-200 characters.
    """
    id: uuid.UUID = Field(description="Unique note identifier")
    image_url: str = Field(description="URL to uploaded image thumbnail")
    text_preview: str = Field(description="First 200 characters of parsed text")
    created_at: datetime = Field(description="Creation timestamp (UTC)")
    status: str = Field(description="Processing state")

    model_config = {"from_attributes": True}


class NoteListResponse(BaseModel):
    """
    What:  Paginated response wrapper for the notes list endpoint.
    Who:   Returned by GET /api/notes.
    
    Pagination strategy:
        We use cursor-based pagination (not offset-based) because:
        1. Consistent results when new notes are added during pagination
           (offset-based would skip/duplicate items)
        2. Better performance on large datasets (no OFFSET scan)
        3. Natural fit for "load more" / infinite scroll UIs
        
    How cursor works:
        - next_cursor: The created_at value of the last item in the current page
        - Client sends cursor as query param to get the next page
        - Server uses WHERE created_at < :cursor for next page
    """
    notes: List[NoteListItem] = Field(description="Array of note summaries")
    total_count: int = Field(description="Total number of notes matching filters")
    next_cursor: Optional[str] = Field(
        default=None,
        description="Cursor for next page (ISO datetime). Null if no more pages."
    )
    has_more: bool = Field(description="Whether more pages are available")


class ParseResponse(BaseModel):
    """
    What:  Response after successfully parsing a handwritten note image.
    Who:   Returned by POST /api/parse with HTTP 201 Created.
    When:  After image upload, validation, Gemini processing, and DB storage.
    
    Why include both parsed_text and note:
        - parsed_text at top level: Quick access for immediate display
        - note object: Full note data for adding to client-side cache
    """
    message: str = Field(
        default="Note parsed successfully",
        description="Human-readable success message"
    )
    parsed_text: str = Field(description="Extracted text from the handwritten image")
    note: NoteResponse = Field(description="Full note object including metadata")


# ══════════════════════════════════════════════════════════════════════════
# Query Parameter Models — What the client sends in URL params
# ══════════════════════════════════════════════════════════════════════════


class PaginationParams(BaseModel):
    """
    What:  Validated query parameters for paginated note listing.
    How:   FastAPI extracts these from query string and validates types/ranges.
    
    Parameters:
        limit: Items per page (1-100, default 20)
            Why max 100: Prevents clients from requesting entire dataset
            Why default 20: Good balance of content density and load speed
        
        cursor: ISO datetime string for cursor-based pagination
            What: The created_at value of the last item from the previous page
            Why string (not datetime): Query params are always strings; we parse later
        
        from_date / to_date: Optional date range filter
            Format: ISO 8601 (e.g., "2024-01-15T00:00:00Z")
            Why optional: Most users want all notes; power users filter by date
        
        sort: Sort direction for results
            Why only two options: created_at is the only sortable field
            (adding more would require additional indexes)
    """
    limit: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")
    cursor: Optional[str] = Field(default=None, description="Pagination cursor (ISO datetime)")
    from_date: Optional[str] = Field(default=None, description="Filter start date (ISO 8601)")
    to_date: Optional[str] = Field(default=None, description="Filter end date (ISO 8601)")
    sort: str = Field(
        default="created_at_desc",
        description="Sort order: created_at_desc (newest first) or created_at_asc"
    )

    @field_validator("sort")
    @classmethod
    def validate_sort(cls, v: str) -> str:
        """Ensures sort parameter is a valid option."""
        valid = {"created_at_desc", "created_at_asc"}
        if v not in valid:
            raise ValueError(f"Invalid sort '{v}'. Must be one of: {valid}")
        return v


# ══════════════════════════════════════════════════════════════════════════
# Error Response Models — Consistent error format across all endpoints
# ══════════════════════════════════════════════════════════════════════════


class ErrorResponse(BaseModel):
    """
    What:  Standardized error response format for all API errors.
    Why:   Clients need a consistent structure to parse errors programmatically.
    
    Fields:
        error: Machine-readable error code (e.g., "validation_error", "not_found")
        message: Human-readable description for display to users
        details: Optional extra context (e.g., which field failed validation)
        request_id: Correlation ID for tracing this error in server logs
    
    Example:
        {
            "error": "validation_error",
            "message": "File type 'application/pdf' is not supported",
            "details": {"allowed_types": ["png", "jpg", "jpeg"]},
            "request_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    """
    error: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error description")
    details: Optional[dict] = Field(default=None, description="Additional error context")
    request_id: Optional[str] = Field(default=None, description="Request correlation ID")


class HealthResponse(BaseModel):
    """
    What:  Health check response showing service and dependency status.
    Who:   Returned by GET /health for monitoring and load balancer health checks.
    
    Why check dependencies:
        A healthy backend that can't reach its database is effectively down.
        Health checks should verify the entire chain, not just "is the process running?"
    """
    status: str = Field(description="Overall service status: healthy, degraded, unhealthy")
    version: str = Field(description="Application version")
    database: str = Field(description="Database connectivity: connected, disconnected")
    gemini: str = Field(description="Gemini API status: available, unavailable, circuit_open")
    uptime_seconds: float = Field(description="Seconds since service started")
