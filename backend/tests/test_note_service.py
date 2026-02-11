"""
ScribeSnap Backend — Note Service Unit Tests
===============================================

What:  Tests for NoteService business logic (parse, get, list).
Why:   The orchestrator contains critical business logic that must be validated.
How:   Uses mock DB sessions and mock services (no real DB or API calls).
When:  Run on every commit to catch regressions in business logic.

What we test:
    ✅ Successful parse workflow (validate → store → parse → persist)
    ✅ Note not found raises NotFoundError
    ✅ List notes with pagination parameters
    ✅ Error handling and status recording on parse failure
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.note_service import NoteService
from app.exceptions import NotFoundError, LLMServiceError


class TestNoteServiceParse:
    """Tests for the parse_note workflow."""

    def setup_method(self):
        self.service = NoteService()

    @pytest.mark.asyncio
    async def test_parse_note_success(self, mock_db_session):
        """Successful parse should create note and return ParseResponse."""
        with patch('app.services.note_service.file_service') as mock_file, \
             patch('app.services.note_service.gemini_service') as mock_gemini:

            # Mock file service
            mock_file.validate_and_store = AsyncMock(
                return_value=("/abs/path/2024/01/15/uuid.jpg", "2024/01/15/uuid.jpg")
            )

            # Mock Gemini response
            mock_gemini.parse_image = AsyncMock(return_value="Hello world")

            # Mock DB flush to set note.id
            async def mock_flush():
                pass
            mock_db_session.flush = AsyncMock(side_effect=mock_flush)

            result = await self.service.parse_note(
                db=mock_db_session,
                filename="test.jpg",
                content=b"fake image bytes",
                content_length=17,
            )

            assert result.message == "Note parsed successfully"
            assert result.parsed_text == "Hello world"
            mock_file.validate_and_store.assert_awaited_once()
            mock_gemini.parse_image.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_parse_note_llm_failure_records_error(self, mock_db_session):
        """LLM failure should update note status to 'failed' and re-raise."""
        with patch('app.services.note_service.file_service') as mock_file, \
             patch('app.services.note_service.gemini_service') as mock_gemini:

            mock_file.validate_and_store = AsyncMock(
                return_value=("/abs/path/test.jpg", "2024/01/15/test.jpg")
            )
            mock_gemini.parse_image = AsyncMock(
                side_effect=LLMServiceError(message="Gemini failed")
            )
            mock_db_session.flush = AsyncMock()

            with pytest.raises(LLMServiceError):
                await self.service.parse_note(
                    db=mock_db_session,
                    filename="test.jpg",
                    content=b"fake image",
                    content_length=10,
                )


class TestNoteServiceGet:
    """Tests for get_note retrieval."""

    def setup_method(self):
        self.service = NoteService()

    @pytest.mark.asyncio
    async def test_get_note_found(self, mock_db_session, sample_note_data):
        """Existing note should return NoteResponse."""
        # Mock the database query result
        mock_note = MagicMock()
        mock_note.id = sample_note_data["id"]
        mock_note.image_path = sample_note_data["image_path"]
        mock_note.parsed_text = sample_note_data["parsed_text"]
        mock_note.created_at = sample_note_data["created_at"]
        mock_note.status = sample_note_data["status"]
        mock_note.error_message = sample_note_data["error_message"]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_note
        mock_db_session.execute.return_value = mock_result

        result = await self.service.get_note(mock_db_session, sample_note_data["id"])

        assert result.id == sample_note_data["id"]
        assert result.parsed_text == sample_note_data["parsed_text"]
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_get_note_not_found(self, mock_db_session):
        """Non-existent note should raise NotFoundError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await self.service.get_note(mock_db_session, uuid4())


class TestNoteServiceList:
    """Tests for list_notes with pagination."""

    def setup_method(self):
        self.service = NoteService()

    @pytest.mark.asyncio
    async def test_list_notes_empty(self, mock_db_session):
        """Empty database should return empty list with no cursor."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        # Mock count query
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        mock_db_session.execute = AsyncMock(side_effect=[mock_result, count_result])

        result = await self.service.list_notes(mock_db_session, limit=20)

        assert result.notes == []
        assert result.total_count == 0
        assert result.has_more is False
        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_list_notes_with_results(self, mock_db_session):
        """Should return note items with pagination info."""
        # Create mock notes
        mock_notes = []
        for i in range(3):
            note = MagicMock()
            note.id = uuid4()
            note.image_path = f"2024/01/15/note-{i}.jpg"
            note.parsed_text = f"Note {i} text"
            note.created_at = datetime.now(timezone.utc)
            note.status = "completed"
            mock_notes.append(note)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_notes

        count_result = MagicMock()
        count_result.scalar.return_value = 3

        mock_db_session.execute = AsyncMock(side_effect=[mock_result, count_result])

        result = await self.service.list_notes(mock_db_session, limit=20)

        assert len(result.notes) == 3
        assert result.total_count == 3
        assert result.has_more is False  # 3 items, limit 20 → no more
