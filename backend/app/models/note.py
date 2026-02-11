"""
ScribeSnap Backend — Note SQLAlchemy Model
============================================

What:  ORM model representing the `notes` table in PostgreSQL.
Why:   Maps Python objects to database rows for type-safe database operations.
How:   Inherits from SQLAlchemy's DeclarativeBase; Alembic reads this for migrations.
Who:   Used by NoteService for CRUD operations and by Alembic for schema management.
When:  Instantiated when creating new notes; queried when listing/fetching notes.

Table Design Rationale:
    - UUID primary key: Non-sequential (security), globally unique (distributed-ready)
    - image_path: Relative path from storage root (portable across environments)
    - parsed_text: Full extracted text (not truncated — we truncate in the API layer)
    - status: Tracks processing state for potential async workflows
    - error_message: Stored for debugging failed parses (shown to user for transparency)
    - retry_count: Tracks how many times Gemini was called (useful for cost analysis)
    - created_at: UTC with timezone for global consistency (never use naive datetimes)
    
    Index on created_at DESC:
        Optimizes the most common query pattern: "show me my recent notes"
        Without this index, PostgreSQL would do a sequential scan on every history page load
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP

from app.database import Base


class Note(Base):
    """
    Represents a parsed handwritten note in the database.
    
    Lifecycle:
        1. Created when user uploads an image (status = 'processing')
        2. Updated after Gemini returns parsed text (status = 'completed')
        3. On Gemini failure: status = 'failed', error_message populated
        4. Never deleted — immutable after completion (simplifies caching)
    
    Query Patterns:
        - List recent notes: SELECT ... ORDER BY created_at DESC LIMIT 20
          → Uses idx_notes_created_at index for O(log n) performance
        - Get single note: SELECT ... WHERE id = :uuid
          → Uses primary key index for O(1) lookup
        - Filter by date: SELECT ... WHERE created_at BETWEEN :from AND :to
          → Uses idx_notes_created_at for range scan
    """

    __tablename__ = "notes"

    # ── Primary Key ───────────────────────────────────────────────────────
    # Why UUID: Non-sequential IDs prevent enumeration attacks (can't guess next ID)
    # Why server-side default: gen_random_uuid() is faster than generating in Python
    # and ensures uniqueness even with concurrent inserts from multiple workers
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Unique identifier — UUID for distributed compatibility and security",
    )

    # ── Image Path ────────────────────────────────────────────────────────
    # What: Relative path from STORAGE_ROOT to the uploaded image file
    # Format: YYYY/MM/DD/<uuid>.<ext> (e.g., 2024/01/15/abc123.jpg)
    # Why relative: Portable between environments (Docker vs local)
    # Why not store the image as BLOB: Files on disk are faster to serve,
    # don't bloat the database, and can be CDN-backed in production
    image_path: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Relative path from storage root to the uploaded image",
    )

    # ── Parsed Text ───────────────────────────────────────────────────────
    # What: The full text extracted from the handwritten image by Gemini
    # Why TEXT (not VARCHAR): No artificial length limit on extracted content;
    # handwritten notes can be arbitrarily long
    # Why NOT NULL: If parsing fails, the Note is stored with status='failed'
    # and an error_message instead of an empty parsed_text
    parsed_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="Full text extracted from the image by Gemini Vision API",
    )

    # ── Timestamps ────────────────────────────────────────────────────────
    # Why TIMESTAMP WITH TIME ZONE: Unambiguous time representation globally
    # Why UTC: All storage in UTC; conversion to local time happens in the frontend
    # This prevents timezone bugs when users or servers are in different zones
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        comment="When this note was created (UTC)",
    )

    # ── Processing Status ─────────────────────────────────────────────────
    # What: Tracks the current processing state of this note
    # Values: 'processing' → 'completed' | 'failed'
    # Why stored: Enables async processing workflows where upload and parsing
    # happen in separate steps (future: message queue integration)
    # Why VARCHAR(50): Short enum-like value; doesn't warrant a separate table
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="processing",
        server_default=text("'processing'"),
        comment="Processing state: processing, completed, failed",
    )

    # ── Error Tracking ────────────────────────────────────────────────────
    # What: Stores error details when parsing fails
    # Why stored (not just logged): Enables user-facing error messages and
    # allows support staff to debug issues without searching logs
    # Why nullable: Only populated on failure; NULL means no error
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Error details when parsing fails — for debugging and user feedback",
    )

    # What: Number of Gemini API call attempts for this note
    # Why tracked: Useful for cost analysis and identifying problematic images
    # that consistently cause retries (e.g., very low quality handwriting)
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Number of Gemini API retry attempts",
    )

    # ── Indexes ───────────────────────────────────────────────────────────
    # created_at DESC index: Optimizes the primary query pattern (recent notes first)
    # Without this, listing notes would require a full table scan + sort
    # Performance: O(log n) lookup + sequential scan of result set
    __table_args__ = (
        Index("idx_notes_created_at", created_at.desc()),
    )

    def __repr__(self) -> str:
        """Developer-friendly string representation for debugging."""
        return (
            f"<Note(id={self.id}, status='{self.status}', "
            f"created_at='{self.created_at}')>"
        )
