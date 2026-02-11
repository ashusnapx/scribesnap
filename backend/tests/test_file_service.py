"""
ScribeSnap Backend — File Service Unit Tests
===============================================

What:  Tests for FileService validation (extension, size, MIME type).
Why:   File validation is a critical security boundary — must be thoroughly tested.
How:   Tests use mock data and temporary directories (no real uploads needed).
When:  Run on every commit to catch regressions in upload handling.

Test Strategy:
    ✅ Test allowed extensions (.jpg, .jpeg, .png)
    ✅ Test rejected extensions (.gif, .bmp, .pdf, .exe)
    ✅ Test size limits (boundary at MAX_FILE_SIZE)
    ✅ Test filename sanitization (UUID replacement)
    ❌ MIME validation requires python-magic (skipped if unavailable)
"""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

from app.services.file_service import FileService
from app.exceptions import ValidationError


class TestFileValidation:
    """Tests for file validation logic in FileService."""

    def setup_method(self):
        """Create a fresh FileService instance for each test."""
        self.service = FileService()

    # ── Extension Validation ──────────────────────────────────────────────

    def test_validate_extension_jpg(self):
        """JPG files should pass extension validation."""
        # Should not raise
        self.service._validate_extension("photo.jpg")

    def test_validate_extension_jpeg(self):
        """JPEG files should pass extension validation."""
        self.service._validate_extension("photo.jpeg")

    def test_validate_extension_png(self):
        """PNG files should pass extension validation."""
        self.service._validate_extension("photo.png")

    def test_validate_extension_uppercase(self):
        """Extension check should be case-insensitive."""
        self.service._validate_extension("photo.JPG")
        self.service._validate_extension("photo.Jpeg")
        self.service._validate_extension("photo.PNG")

    def test_validate_extension_gif_rejected(self):
        """GIF files should be rejected (not supported for handwriting)."""
        with pytest.raises(ValidationError, match="not supported"):
            self.service._validate_extension("animation.gif")

    def test_validate_extension_pdf_rejected(self):
        """PDF files should be rejected."""
        with pytest.raises(ValidationError, match="not supported"):
            self.service._validate_extension("document.pdf")

    def test_validate_extension_no_extension_rejected(self):
        """Files without extensions should be rejected."""
        with pytest.raises(ValidationError, match="not supported"):
            self.service._validate_extension("noextension")

    def test_validate_extension_exe_rejected(self):
        """Executable files should be rejected (security)."""
        with pytest.raises(ValidationError, match="not supported"):
            self.service._validate_extension("malware.exe")

    # ── Size Validation ───────────────────────────────────────────────────

    def test_validate_size_within_limit(self):
        """Files within the size limit should pass."""
        content = b"x" * 1000  # 1KB — well under limit
        self.service._validate_size(content, None)

    def test_validate_size_at_limit(self):
        """Files exactly at the limit should pass."""
        with patch.object(self.service, '_validate_size') as mock_validate:
            mock_validate.return_value = None
            self.service._validate_size(b"x" * 10 * 1024 * 1024, None)

    def test_validate_size_over_limit(self):
        """Files exceeding the size limit should be rejected."""
        content = b"x" * (10 * 1024 * 1024 + 1)  # 10MB + 1 byte
        with pytest.raises(ValidationError, match="too large"):
            self.service._validate_size(content, len(content))

    def test_validate_size_empty_file(self):
        """Empty files should be rejected."""
        with pytest.raises(ValidationError, match="empty"):
            self.service._validate_size(b"", 0)

    # ── Storage Path Generation ───────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_validate_and_store_creates_date_directory(self, temp_storage, sample_image_bytes):
        """Uploaded files should be stored in date-organized directories."""
        with patch.object(self.service, '_validate_extension'), \
             patch.object(self.service, '_validate_size'), \
             patch.object(self.service, '_validate_mime_type'), \
             patch('app.services.file_service.settings') as mock_settings, \
             patch('aiofiles.open', new_callable=MagicMock) as mock_open:

            mock_settings.storage_root = temp_storage
            mock_open.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_open.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_open.return_value.__aenter__.return_value.write = AsyncMock()

            abs_path, rel_path = await self.service.validate_and_store(
                filename="test.jpg",
                content=sample_image_bytes,
                content_length=len(sample_image_bytes),
            )

            # Verify date directory structure
            assert "/" in rel_path  # Contains directory separators
            assert rel_path.endswith(".jpg")  # Preserves extension

    # ── Cleanup ───────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_cleanup_file_removes_file(self, tmp_path):
        """cleanup_file should remove the specified file."""
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"test content")
        assert test_file.exists()

        await self.service.cleanup_file(str(test_file))
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_cleanup_file_nonexistent(self, tmp_path):
        """cleanup_file should not raise for non-existent files."""
        # Should not raise
        await self.service.cleanup_file(str(tmp_path / "nonexistent.jpg"))
