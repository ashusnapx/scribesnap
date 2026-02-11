"""Create notes table

Revision ID: 001
Revises: None
Create Date: 2024-01-15 00:00:00.000000+00:00

What:  Creates the initial `notes` table for storing parsed handwritten notes.
Why:   Core data model for the application — every parsed image becomes a row here.
How:   Uses PostgreSQL-specific features: UUID primary key, TIMESTAMP WITH TIME ZONE.

Rollback: downgrade() drops the table entirely (destructive — all data lost).
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create the notes table with all columns, constraints, and indexes.
    
    Column rationale documented inline — see app/models/note.py for full docs.
    """
    op.create_table(
        "notes",

        # Primary Key: UUID for distributed compatibility and security
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Unique identifier — UUID for distributed compatibility and security",
        ),

        # Relative path from storage root to uploaded image
        sa.Column(
            "image_path",
            sa.String(255),
            nullable=False,
            comment="Relative path from storage root to the uploaded image",
        ),

        # Full extracted text (no length limit — TEXT type)
        sa.Column(
            "parsed_text",
            sa.Text(),
            nullable=False,
            server_default=sa.text("''"),
            comment="Full text extracted from the image by Gemini Vision API",
        ),

        # UTC timestamp with timezone awareness
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="When this note was created (UTC)",
        ),

        # Processing status: processing → completed | failed
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'processing'"),
            comment="Processing state: processing, completed, failed",
        ),

        # Error message for failed parses
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error details when parsing fails — for debugging and user feedback",
        ),

        # Retry count for cost tracking
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Number of Gemini API retry attempts",
        ),

        # Primary key constraint
        sa.PrimaryKeyConstraint("id"),
    )

    # Index on created_at DESC for optimizing "recent notes" queries
    # Why: The most common query is "show me my latest notes" (ORDER BY created_at DESC)
    # Without this index, PostgreSQL would do a sequential scan on every page load
    op.create_index(
        "idx_notes_created_at",
        "notes",
        [sa.text("created_at DESC")],
    )


def downgrade() -> None:
    """
    Drop the notes table entirely.
    
    WARNING: This is destructive — all note data will be permanently lost.
    In production, you would typically NOT allow downgrades for tables with data.
    Instead, create a new forward migration that archives data first.
    """
    op.drop_index("idx_notes_created_at", table_name="notes")
    op.drop_table("notes")
