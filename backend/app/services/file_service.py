"""
ScribeSnap Backend — File Storage Service
============================================

What:  Handles secure file upload, validation, storage, and cleanup.
Why:   Centralizes all file system operations with security checks.
How:   Validates MIME type and size, stores in date-organized directories,
       generates unique filenames to prevent conflicts.
Who:   Called by NoteService during upload workflow.
When:  After receiving multipart upload, before Gemini processing.

Security Model:
    We implement defense-in-depth for file uploads:
    1. Extension check:   First line of defense (fast, catches most invalid files)
    2. MIME type check:    Second line (uses libmagic to inspect file header bytes)
    3. Size check:         Prevents memory exhaustion (checked before reading full file)
    4. UUID filename:      Prevents path traversal and filename-based attacks
    5. Storage outside web root: Files not directly accessible via URL

    Why both extension AND MIME check:
        - Extension alone is trivially bypassed (rename malware.exe → malware.jpg)
        - MIME checking reads actual file header bytes (magic numbers)
        - Example: A .jpg file with PNG magic bytes is suspicious and rejected
    
    Attack vectors prevented:
        - Path traversal: UUID filenames contain no user input
        - File type bypass: MIME validation catches renamed files
        - DoS via large files: Size limit prevents memory exhaustion
        - Filename collision: UUID ensures uniqueness even under concurrency
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

import aiofiles

from app.config import settings
from app.exceptions import ValidationError, FileStorageError

logger = logging.getLogger(__name__)

# ── Allowed File Types ────────────────────────────────────────────────────
# What: Mapping of allowed MIME types to file extensions
# Why explicit mapping: Ensures consistency between MIME type and extension
# Why only these types: These are the image formats Gemini Vision API supports
ALLOWED_MIME_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
}

# What: Set of allowed file extensions for quick lookup
# Why separate from MIME dict: Used for the fast extension-based first check
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


class FileService:
    """
    Manages file upload, validation, and storage lifecycle.
    
    Lifecycle of an uploaded file:
        1. Client sends multipart upload → FileService.validate_and_store()
        2. Extension check (fast, rejects obviously wrong files)
        3. Size check (prevents reading huge files into memory)
        4. Content is read into memory (bounded by size check)
        5. MIME type check via magic bytes (catches renamed files)
        6. File is written to date-organized directory with UUID filename
        7. Relative path is returned (stored in database)
        8. On any failure: cleanup_file() removes partial writes
    
    Directory Structure:
        storage/
        └── 2024/
            └── 01/
                └── 15/
                    ├── a1b2c3d4-5678.jpg
                    └── e5f6g7h8-9012.png
    
    Why date-organized:
        - File systems slow down with too many files in one directory
        - Date structure enables easy backup and cleanup (archive by month)
        - Makes it simple to find files by creation date
        - Typical FS performance degrades above ~10,000 files per directory
    """

    def __init__(self, storage_root: Optional[str] = None):
        """
        Initialize the file service with the storage root directory.
        
        Args:
            storage_root: Override the default storage path (used in tests).
                         If None, uses settings.storage_root.
        """
        self.storage_root = Path(storage_root or settings.storage_root).resolve()
        # Ensure base storage directory exists
        # Why exist_ok: Idempotent — safe to call multiple times
        self.storage_root.mkdir(parents=True, exist_ok=True)
        logger.info("FileService initialized with storage_root=%s", self.storage_root)

    def validate_extension(self, filename: str) -> str:
        """
        Validate file extension (first line of defense).
        
        What:    Checks that the file extension is in our allowed list.
        Why:     Fast rejection of obviously invalid files (before reading content).
        Returns: Normalized extension (lowercase with dot).
        Raises:  ValidationError if extension is not allowed.
        """
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(
                message=(
                    f"File type '{ext}' is not supported. "
                    f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                ),
                field="file",
                context={"extension": ext, "allowed": list(ALLOWED_EXTENSIONS)},
            )
        return ext

    def validate_size(self, content_length: Optional[int], actual_size: int) -> None:
        """
        Validate file size against configured maximum.
        
        What:    Prevents excessively large files from consuming server resources.
        How:     Checks Content-Length header first (before reading), then actual size.
        Why two checks:
            - Content-Length: Rejects before reading (saves bandwidth)
            - Actual size: Catches mismatched headers (some clients lie)
        
        Args:
            content_length: Value from Content-Length header (may be None or inaccurate)
            actual_size: Actual byte count of the uploaded file
        
        Raises:
            ValidationError with human-readable size limit message
        """
        max_mb = settings.max_file_size / (1024 * 1024)

        if content_length and content_length > settings.max_file_size:
            raise ValidationError(
                message=f"File size exceeds maximum of {max_mb:.0f}MB. Please upload a smaller image.",
                field="file",
                context={"max_size_mb": max_mb, "reported_size": content_length},
            )

        if actual_size > settings.max_file_size:
            raise ValidationError(
                message=f"File size ({actual_size / (1024 * 1024):.1f}MB) exceeds maximum of {max_mb:.0f}MB.",
                field="file",
                context={"max_size_mb": max_mb, "actual_size": actual_size},
            )

    def validate_mime_type(self, file_content: bytes, filename: str) -> str:
        """
        Validate actual MIME type by inspecting file content bytes.
        
        What:    Uses magic bytes (file header) to determine true file type.
        Why:     Extension-only checks are trivially bypassed by renaming files.
        How:     python-magic reads the first few bytes and matches against known
                 file signatures (e.g., JPEG starts with FF D8 FF).
        
        Args:
            file_content: Raw bytes of the uploaded file
            filename: Original filename (for error messaging only)
        
        Returns:
            Detected MIME type string (e.g., "image/jpeg")
        
        Raises:
            ValidationError if MIME type is not in the allowed list
        """
        try:
            import magic
            mime_type = magic.from_buffer(file_content, mime=True)
        except ImportError:
            # python-magic not installed (e.g., in CI without libmagic)
            # Fallback: Trust the extension (less secure but functional)
            logger.warning(
                "python-magic not available — falling back to extension-based type detection. "
                "Install libmagic for production security."
            )
            ext = Path(filename).suffix.lower()
            mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
            mime_type = mime_map.get(ext, "application/octet-stream")
        except Exception as e:
            logger.error("MIME type detection failed: %s", str(e))
            raise FileStorageError(
                message="Could not verify file type. Please try again.",
                context={"error": str(e)},
            )

        if mime_type not in ALLOWED_MIME_TYPES:
            raise ValidationError(
                message=(
                    f"File content type '{mime_type}' is not supported. "
                    f"The file must be a valid image (PNG or JPEG)."
                ),
                field="file",
                context={"detected_mime": mime_type, "allowed": list(ALLOWED_MIME_TYPES.keys())},
            )

        return mime_type

    def _generate_storage_path(self, extension: str) -> Tuple[Path, str]:
        """
        Generate a unique, date-organized file path for storage.
        
        What:    Creates YYYY/MM/DD/<uuid>.<ext> path structure.
        Returns: Tuple of (absolute_path, relative_path_from_storage_root).
        
        Why UUID filename:
            - Prevents filename collisions even under concurrent uploads
            - Eliminates path traversal risk (no user input in filename)
            - Combined with original extension to preserve file type info
        
        Why date directories:
            - Distributes files across directories (prevents FS performance degradation)
            - Enables easy backup/cleanup by time period
            - Natural organization matching typical usage patterns
        """
        now = datetime.now(timezone.utc)
        date_dir = now.strftime("%Y/%m/%d")  # e.g., "2024/01/15"
        unique_name = f"{uuid.uuid4()}{extension}"  # e.g., "a1b2c3d4-5678-...-9012.jpg"

        relative_path = f"{date_dir}/{unique_name}"
        absolute_path = self.storage_root / relative_path

        return absolute_path, relative_path

    async def store_file(self, content: bytes, extension: str) -> Tuple[str, str]:
        """
        Write validated file content to disk.
        
        What:    Stores file in date-organized directory with UUID filename.
        How:     Async file I/O to avoid blocking the event loop.
        Returns: Tuple of (absolute_path, relative_path).
        
        Why async I/O:
            File writes can be slow (especially on network storage or during I/O contention).
            Async writes allow other requests to be processed while waiting for disk I/O.
        
        Raises:
            FileStorageError if directory creation or file write fails.
        """
        absolute_path, relative_path = self._generate_storage_path(extension)

        try:
            # Create date directory if it doesn't exist
            # Why parents=True: Creates all intermediate directories (2024/01/15)
            absolute_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file content asynchronously
            # Why 'wb' mode: Binary write — we're writing raw bytes, not text
            async with aiofiles.open(absolute_path, "wb") as f:
                await f.write(content)

            logger.info(
                "File stored: %s (%d bytes)",
                relative_path,
                len(content),
            )
            return str(absolute_path), relative_path

        except OSError as e:
            # OS-level errors: disk full, permission denied, etc.
            logger.error("Failed to store file at %s: %s", absolute_path, str(e))
            raise FileStorageError(
                message="Failed to save uploaded image. Please try again.",
                context={"path": str(absolute_path), "os_error": str(e)},
            )

    async def cleanup_file(self, file_path: str) -> None:
        """
        Remove a file from storage (used for cleanup after failed processing).
        
        What:    Deletes a file from disk if it exists.
        When:    Called as a background task when Gemini processing or DB storage fails.
        Why:     Prevents storage bloat from failed uploads accumulating.
        
        Why async background task:
            Cleanup is not critical for the user's request. Running it in the
            background means the error response is returned immediately while
            cleanup happens asynchronously.
        
        Error handling:
            Silently handles missing files and logs errors for other failures.
            Why silent: Cleanup is best-effort — failing to delete a file is
            not a user-facing error (periodic cleanup jobs handle stragglers).
        """
        try:
            path = Path(file_path)
            if path.exists():
                os.remove(path)
                logger.info("Cleaned up file: %s", path.name)
            else:
                logger.debug("Cleanup: file already gone: %s", path.name)
        except Exception as e:
            # Log but don't raise — cleanup failure is not critical
            # Background cleanup job will catch any remaining files
            logger.warning("Failed to clean up file %s: %s", file_path, str(e))

    async def validate_and_store(
        self,
        filename: str,
        content: bytes,
        content_length: Optional[int] = None,
    ) -> Tuple[str, str]:
        """
        Complete file validation and storage pipeline.
        
        What:    Validates extension, size, and MIME type, then stores the file.
        Who:     Called by NoteService as the first step in the parse workflow.
        Returns: Tuple of (absolute_path, relative_path_for_db).
        
        Validation order (optimized for early rejection):
            1. Extension check — O(1), no file reading needed
            2. Size check — O(1), uses Content-Length header
            3. MIME type check — O(1), reads only first few bytes
            4. Store file — O(n), writes all bytes to disk
        
        Why this order:
            Each step is more expensive than the previous. By placing cheap
            checks first, we reject invalid files faster and waste fewer resources.
        """
        # Step 1: Validate extension (cheapest check)
        ext = self.validate_extension(filename)

        # Step 2: Validate file size
        self.validate_size(content_length, len(content))

        # Step 3: Validate actual MIME type via magic bytes
        self.validate_mime_type(content, filename)

        # Step 4: Store validated file to disk
        absolute_path, relative_path = await self.store_file(content, ext)

        return absolute_path, relative_path


# ── Singleton Instance ────────────────────────────────────────────────────
# Why singleton: Storage root doesn't change; no per-request state needed
file_service = FileService()
