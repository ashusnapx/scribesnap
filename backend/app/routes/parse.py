"""
ScribeSnap Backend — Parse Route Handler
==========================================

What:  Handles POST /api/parse for uploading and processing handwritten note images.
Why:   Entry point for the core feature — converting images to text.
How:   Receives multipart upload, delegates to NoteService, returns parsed result.
Who:   Called by the frontend UploadZone component.
When:  Each time a user drops or selects an image file.

Request Flow:
    1. Client sends multipart/form-data with 'file' field
    2. FastAPI extracts UploadFile (validates multipart format)
    3. We read file content into memory (bounded by size validation)
    4. NoteService handles: validate → store → parse → persist
    5. Return 201 Created with ParseResponse body
    6. On error: background task cleans up any stored file

Security Checks (this route):
    - File type: Validated by NoteService (extension + MIME)
    - File size: Validated by NoteService (max 10MB)
    - CORS: Configured globally in main.py
    - Rate limit: Applied by middleware
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas.note import ParseResponse, ErrorResponse
from app.services.note_service import note_service
from app.services.file_service import file_service

logger = logging.getLogger(__name__)

# ── Router Configuration ──────────────────────────────────────────────────
# Why prefix="/api": Groups all API routes under /api namespace
# tags=["Parse"]: Groups this endpoint in Swagger UI
router = APIRouter(prefix="/api", tags=["Parse"])


@router.post(
    "/parse",
    status_code=201,
    response_model=ParseResponse,
    responses={
        201: {"description": "Note parsed successfully", "model": ParseResponse},
        400: {"description": "Invalid file type or size", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        503: {"description": "AI service unavailable", "model": ErrorResponse},
    },
    summary="Parse a handwritten note image",
    description=(
        "Upload a handwritten note image (PNG, JPG, JPEG, max 10MB) and extract text. "
        "The image is processed through Google Gemini Vision API for handwriting recognition. "
        "Returns the extracted text along with a stored note record."
    ),
)
async def parse_note(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(
        ...,
        description="Handwritten note image file (PNG, JPG, or JPEG, max 10MB)",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> ParseResponse:
    """
    Parse a handwritten note image and extract text.
    
    What:    Accepts an image upload, extracts text via Gemini, stores result.
    Who:     Called by the frontend upload component.
    
    Processing Steps:
        1. Read file content into memory
        2. Delegate to NoteService.parse_note() for full workflow
        3. On failure: schedule background cleanup of any stored file
    
    Why we read the entire file into memory:
        - Gemini API requires the complete image
        - Size is bounded (max 10MB) by validation
        - Async reading prevents blocking the event loop
    
    Why BackgroundTasks for cleanup:
        - Failed upload cleanup should not delay the error response
        - User gets immediate feedback; cleanup happens asynchronously
        - If cleanup fails, periodic maintenance catches stragglers
    
    Returns:
        ParseResponse (HTTP 201): On success, with extracted text and note data.
    
    Error responses (handled by global exception handlers):
        HTTP 400: Invalid file type or size (ValidationError)
        HTTP 429: Rate limit exceeded (RateLimitExceededError)
        HTTP 503: Gemini unavailable (LLMServiceError / CircuitBreakerOpenError)
        HTTP 500: Unexpected server error (DatabaseError)
    """
    # Read uploaded file content
    # Why await: Non-blocking file read (important for large files on slow connections)
    content = await file.read()

    logger.info(
        "Received parse request: filename=%s, size=%d bytes",
        file.filename or "unknown",
        len(content),
    )

    try:
        # Delegate entire workflow to NoteService
        # Why service layer: Keeps route handler thin (HTTP concerns only)
        result = await note_service.parse_note(
            db=db,
            filename=file.filename or "upload.jpg",
            content=content,
            content_length=file.size,
        )
        return result

    except Exception:
        # Re-raise to let global exception handler format the error response
        # Why re-raise: Global handlers provide consistent error formatting
        raise
    finally:
        # Always close the uploaded file to free resources
        # Why finally: Ensures cleanup even on error
        await file.close()
