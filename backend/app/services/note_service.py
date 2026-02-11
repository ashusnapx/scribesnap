"""
ScribeSnap Backend — Note Service (Business Logic Orchestrator)
================================================================

What:  Central orchestrator coordinating upload → validate → parse → persist workflow.
Why:   Encapsulates all business logic in one place, independent of HTTP concerns.
How:   Composes FileService, GeminiService, and database operations.
Who:   Called by route handlers; calls services and database layer.
When:  For every note creation and retrieval operation.

Orchestration Flow (POST /api/parse):
    ┌──────────┐    ┌─────────────┐    ┌──────────────┐    ┌──────────┐
    │  Upload  │───▶│  Validate   │───▶│  Gemini API  │───▶│  Store   │
    │  (Route) │    │  & Store    │    │  (Parse)     │    │  (DB)    │
    └──────────┘    │  (FileServ) │    │  (GeminiServ)│    └──────────┘
                    └─────────────┘    └──────────────┘
    
    On failure at any step:
    - File cleanup runs as background task
    - Error is recorded in database (if note was created)
    - Appropriate exception propagates to error handler

Design Decision:
    NoteService is stateless — it receives dependencies (db session, services)
    for each call. This enables:
    1. Easy testing: Mock any dependency independently
    2. Transaction safety: Each call gets its own session
    3. No thread-safety concerns: No shared mutable state
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, DatabaseError, LLMServiceError
from app.models.note import Note
from app.schemas.note import (
    NoteResponse,
    NoteListItem,
    NoteListResponse,
    ParseResponse,
)
from app.services.file_service import file_service
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


class NoteService:
    """
    Business logic layer for note operations.
    
    Responsibilities:
        - parse_note(): Complete upload-to-result workflow
        - get_note(): Single note retrieval with not-found handling
        - list_notes(): Paginated listing with cursor-based pagination
    
    Error Handling Strategy:
        Each method handles errors from its sub-operations and translates them
        into appropriate application exceptions. Database errors are wrapped
        in DatabaseError (hides internal details). Service errors propagate
        their original type (LLMServiceError, CircuitBreakerOpenError).
    """

    async def parse_note(
        self,
        db: AsyncSession,
        filename: str,
        content: bytes,
        content_length: Optional[int] = None,
    ) -> ParseResponse:
        """
        Complete workflow: validate → store file → parse with Gemini → save to DB.
        
        What:    Processes an uploaded handwritten note image end-to-end.
        Who:     Called by POST /api/parse route handler.
        When:    On each new image upload from the frontend.
        
        Workflow Steps:
            1. Validate file (extension, size, MIME) and store to disk
            2. Create initial Note record (status='processing')
            3. Send to Gemini for text extraction
            4. Update Note with parsed text (status='completed')
            5. Return ParseResponse with full note data
        
        Error Recovery:
            Step 1 fails → ValidationError (400), no cleanup needed
            Step 2 fails → DatabaseError (500), cleanup file
            Step 3 fails → LLMServiceError (503), update Note status='failed'
            Step 4 fails → DatabaseError (500), note remains as 'processing'
        
        Args:
            db: Async database session (injected by FastAPI)
            filename: Original filename from the upload
            content: Raw file bytes
            content_length: Content-Length header value (may be None)
        
        Returns:
            ParseResponse with extracted text and full note metadata
        
        Raises:
            ValidationError: Invalid file type or size
            LLMServiceError: Gemini failed after retries
            CircuitBreakerOpenError: Too many recent Gemini failures
            DatabaseError: Database operation failed
        """
        absolute_path: Optional[str] = None
        note: Optional[Note] = None

        try:
            # ── Step 1: Validate and store file ───────────────────────────
            # Why first: Reject invalid files before doing any other work
            # Returns both absolute path (for Gemini) and relative path (for DB)
            absolute_path, relative_path = await file_service.validate_and_store(
                filename=filename,
                content=content,
                content_length=content_length,
            )
            logger.info("File validated and stored: %s", relative_path)

            # ── Step 2: Create initial Note record ────────────────────────
            # Why create before parsing: If Gemini takes long, the note exists in DB
            # with status='processing'. Future: frontend can poll for status.
            note = Note(
                image_path=relative_path,
                parsed_text="",  # Will be updated after Gemini responds
                status="processing",
            )
            db.add(note)
            await db.flush()  # Assigns UUID without committing transaction
            logger.info("Note record created: %s (status=processing)", note.id)

            # ── Step 3: Send to Gemini for text extraction ────────────────
            # Why after DB save: Even if Gemini fails, we have a record to retry later
            parsed_text = await gemini_service.parse_image(absolute_path)

            # ── Step 4: Update Note with parsed result ────────────────────
            note.parsed_text = parsed_text
            note.status = "completed"
            # Flush to persist changes (commit happens in get_db_session)
            await db.flush()
            logger.info("Note %s completed: extracted %d chars", note.id, len(parsed_text))

            # ── Step 5: Build and return response ─────────────────────────
            return ParseResponse(
                message="Note parsed successfully",
                parsed_text=parsed_text,
                note=NoteResponse(
                    id=note.id,
                    image_url=f"/api/files/{relative_path}",
                    parsed_text=note.parsed_text,
                    created_at=note.created_at,
                    status=note.status,
                    error_message=note.error_message,
                ),
            )

        except (LLMServiceError,) as e:
            # Gemini failed — record the error in the Note record
            # Why record: Enables user to see why parsing failed
            if note:
                note.status = "failed"
                note.error_message = e.message
                note.retry_count += 1
                try:
                    await db.flush()
                except Exception:
                    logger.error("Failed to update note status to 'failed'")
            raise  # Propagate to error handler for 503 response

        except Exception as e:
            # Unexpected error — cleanup the stored file
            # Why cleanup: Don't leave orphaned files on disk
            if absolute_path:
                await file_service.cleanup_file(absolute_path)
            # If it's already one of our custom exceptions, re-raise as-is
            from app.exceptions import ScribeSnapError
            if isinstance(e, ScribeSnapError):
                raise
            # Wrap unknown exceptions in DatabaseError
            logger.error("Unexpected error in parse_note: %s", str(e), exc_info=True)
            raise DatabaseError(
                message="An error occurred while processing your note. Please try again.",
                context={"original_error": type(e).__name__},
            )

    async def get_note(self, db: AsyncSession, note_id: UUID) -> NoteResponse:
        """
        Retrieve a single note by ID.
        
        What:    Fetches a note from the database and returns it as a response model.
        Who:     Called by GET /api/notes/{id} route handler.
        
        Query plan:
            SELECT * FROM notes WHERE id = :uuid
            → Uses PRIMARY KEY index → O(1) lookup (B-tree index on UUID)
        
        Args:
            db: Async database session
            note_id: UUID of the note to retrieve
        
        Returns:
            NoteResponse with full note data
        
        Raises:
            NotFoundError: Note with given ID does not exist (→ 404)
            DatabaseError: Query execution failed (→ 500)
        """
        try:
            result = await db.execute(
                select(Note).where(Note.id == note_id)
            )
            note = result.scalar_one_or_none()

            if note is None:
                # Why custom exception: Converts SQLAlchemy's "None" return
                # into an HTTP 404 response via the global error handler
                raise NotFoundError(resource="note", resource_id=str(note_id))

            return NoteResponse(
                id=note.id,
                image_url=f"/api/files/{note.image_path}",
                parsed_text=note.parsed_text,
                created_at=note.created_at,
                status=note.status,
                error_message=note.error_message,
            )

        except NotFoundError:
            raise  # Already our exception — propagate as-is
        except Exception as e:
            logger.error("Database error fetching note %s: %s", note_id, str(e))
            raise DatabaseError(
                message="Could not retrieve the note. Please try again.",
                context={"note_id": str(note_id)},
            )

    async def list_notes(
        self,
        db: AsyncSession,
        limit: int = 20,
        cursor: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        sort: str = "created_at_desc",
    ) -> NoteListResponse:
        """
        List notes with cursor-based pagination and optional date filtering.
        
        What:    Returns a paginated list of notes with metadata for infinite scroll.
        Who:     Called by GET /api/notes route handler.
        
        Pagination Strategy (Cursor-Based):
            Why cursor-based over offset-based:
            1. Consistent: Adding a new note doesn't shift results on existing pages
               (offset-based would show duplicates or skip items)
            2. Performant: Uses index seek instead of scanning OFFSET rows
               - Offset: O(offset + limit) → slow for deep pages
               - Cursor: O(log n + limit) → constant regardless of page depth
            3. Natural for infinite scroll: Client just tracks the last-seen cursor
        
        How:
            - Default sort: created_at DESC (newest first, most common use case)
            - Cursor: ISO datetime of last item; WHERE created_at < :cursor
            - Returns next_cursor for client to request next page
        
        Query plan (default sort, no filters):
            SELECT * FROM notes WHERE created_at < :cursor
            ORDER BY created_at DESC LIMIT :limit
            → Uses idx_notes_created_at for O(log n) seek + sequential scan
        
        Args:
            db: Async database session
            limit: Maximum items per page (1-100, default 20)
            cursor: ISO datetime cursor from previous page (None for first page)
            from_date: Filter start date (ISO 8601)
            to_date: Filter end date (ISO 8601)
            sort: Sort direction ('created_at_desc' or 'created_at_asc')
        
        Returns:
            NoteListResponse with notes array, total count, next cursor, has_more flag
        """
        try:
            # ── Build query dynamically ───────────────────────────────────
            query = select(Note)

            # Apply cursor for pagination
            # Why: Only fetch records after the last-seen item
            if cursor:
                try:
                    cursor_dt = datetime.fromisoformat(cursor)
                except ValueError:
                    cursor_dt = None  # Invalid cursor — ignore and start from beginning

                if cursor_dt:
                    if sort == "created_at_desc":
                        # For descending: get items OLDER than cursor
                        query = query.where(Note.created_at < cursor_dt)
                    else:
                        # For ascending: get items NEWER than cursor
                        query = query.where(Note.created_at > cursor_dt)

            # Apply date range filters
            # Why optional: Most users want all notes; power users filter
            if from_date:
                try:
                    from_dt = datetime.fromisoformat(from_date)
                    query = query.where(Note.created_at >= from_dt)
                except ValueError:
                    pass  # Invalid date format — silently ignore

            if to_date:
                try:
                    to_dt = datetime.fromisoformat(to_date)
                    query = query.where(Note.created_at <= to_dt)
                except ValueError:
                    pass

            # Apply sort order
            if sort == "created_at_asc":
                query = query.order_by(asc(Note.created_at))
            else:
                query = query.order_by(desc(Note.created_at))

            # Fetch one extra to determine if there are more pages
            # Why limit + 1: Avoids a separate COUNT query for has_more
            query = query.limit(limit + 1)

            # Execute query
            result = await db.execute(query)
            notes = list(result.scalars().all())

            # ── Calculate total count ─────────────────────────────────────
            # Why separate query: COUNT(*) can't share the cursor/limit query
            count_query = select(func.count(Note.id))
            if from_date:
                try:
                    count_query = count_query.where(Note.created_at >= datetime.fromisoformat(from_date))
                except ValueError:
                    pass
            if to_date:
                try:
                    count_query = count_query.where(Note.created_at <= datetime.fromisoformat(to_date))
                except ValueError:
                    pass

            count_result = await db.execute(count_query)
            total_count = count_result.scalar() or 0

            # ── Determine pagination state ────────────────────────────────
            has_more = len(notes) > limit
            if has_more:
                notes = notes[:limit]  # Remove the extra item

            # Build next cursor from last item
            next_cursor = None
            if has_more and notes:
                next_cursor = notes[-1].created_at.isoformat()

            # ── Build response ────────────────────────────────────────────
            note_items = [
                NoteListItem(
                    id=note.id,
                    image_url=f"/api/files/{note.image_path}",
                    text_preview=note.parsed_text[:200] if note.parsed_text else "",
                    created_at=note.created_at,
                    status=note.status,
                )
                for note in notes
            ]

            return NoteListResponse(
                notes=note_items,
                total_count=total_count,
                next_cursor=next_cursor,
                has_more=has_more,
            )

        except Exception as e:
            logger.error("Database error listing notes: %s", str(e), exc_info=True)
            raise DatabaseError(
                message="Could not retrieve notes. Please try again.",
                context={"error_type": type(e).__name__},
            )


# ── Singleton Instance ────────────────────────────────────────────────────
# Why singleton: NoteService is stateless; no per-instance state needed
note_service = NoteService()
