"""
ScribeSnap Backend — Custom Exception Hierarchy
=================================================

What:  Defines application-specific exceptions for different error scenarios.
Why:   Custom exceptions enable targeted error handling with appropriate HTTP
       status codes and user-friendly messages. They replace generic Python
       exceptions that would leak internal details to the client.
How:   Each exception class carries a message and optional context dict.
       Global exception handlers (registered in main.py) catch these and
       return structured JSON error responses with correct HTTP status codes.
Who:   Raised by services and middleware; caught by global handlers.
When:  During request processing when recoverable errors occur.

Exception Hierarchy:
    ScribeSnapError (base)
    ├── ValidationError          → 400 Bad Request (client can fix)
    ├── NotFoundError            → 404 Not Found
    ├── FileStorageError         → 500 Internal Server Error
    ├── LLMServiceError          → 503 Service Unavailable (retry later)
    ├── CircuitBreakerOpenError  → 503 Service Unavailable (circuit open)
    ├── DatabaseError            → 500 Internal Server Error
    └── RateLimitExceededError   → 429 Too Many Requests

Design Decision:
    We use a custom exception hierarchy instead of returning error dicts because:
    1. Exceptions propagate naturally through the call stack (no manual error checking)
    2. Global handlers provide consistent error response formatting
    3. Type-specific catching enables different recovery strategies
    4. FastAPI's exception handlers intercept exceptions cleanly
    Alternative considered: Return Result[T, Error] objects — more functional but
    requires every caller to check success/failure (verbose in Python)
"""

from typing import Any, Dict, Optional


class ScribeSnapError(Exception):
    """
    Base exception for all ScribeSnap application errors.
    
    What:    Root of the exception hierarchy.
    Why:     Enables catching all app errors with a single except clause.
    How:     Stores a human-readable message and optional context for debugging.
    
    Attributes:
        message:  User-facing error description (safe to return in API response)
        context:  Additional debug info (logged but NOT returned to client)
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        context: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        # Why separate context: Allows logging detailed info without exposing
        # internal details (file paths, query text, etc.) to API consumers
        self.context = context or {}
        super().__init__(self.message)


class ValidationError(ScribeSnapError):
    """
    Raised when client input fails validation.
    
    What:    Indicates the client sent invalid data that can be corrected.
    When:    File type mismatch, size exceeded, missing required fields, invalid format.
    HTTP:    400 Bad Request
    
    Why 400 (not 422):
        We use 400 instead of 422 because:
        - 400 is more widely understood by API consumers
        - Our validation is simpler than Pydantic's automatic 422 (which handles
          field-level errors); our custom validation is for business rules
        - FastAPI already handles schema validation with 422
    
    Example response:
        {
            "error": "validation_error",
            "message": "File type 'application/pdf' is not supported. Allowed: png, jpg, jpeg",
            "details": {"field": "file", "allowed_types": ["png", "jpg", "jpeg"]}
        }
    """

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        ctx = context or {}
        if field:
            ctx["field"] = field
        super().__init__(message=message, context=ctx)
        self.field = field


class NotFoundError(ScribeSnapError):
    """
    Raised when a requested resource does not exist.
    
    What:    The client asked for something that doesn't exist in our database.
    When:    GET /api/notes/{id} with a non-existent UUID.
    HTTP:    404 Not Found
    
    Why a custom exception:
        SQLAlchemy returns None for missing records (not an exception).
        We convert None → NotFoundError in the service layer to keep
        HTTP concerns out of the service logic while still enabling
        the correct status code in the response.
    """

    def __init__(
        self,
        resource: str = "resource",
        resource_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        message = f"The requested {resource} was not found"
        if resource_id:
            message = f"{resource} with ID '{resource_id}' was not found"
        ctx = context or {}
        ctx["resource"] = resource
        if resource_id:
            ctx["resource_id"] = resource_id
        super().__init__(message=message, context=ctx)


class FileStorageError(ScribeSnapError):
    """
    Raised when file system operations fail.
    
    What:    Could not read, write, or delete a file on the storage volume.
    When:    Disk full, permission denied, directory not writable, I/O error.
    HTTP:    500 Internal Server Error
    
    Recovery:
        - Log the error with full file path and OS error for debugging
        - Return generic message to client (don't expose file system paths)
        - Background task attempts cleanup of any partial writes
    """

    def __init__(
        self,
        message: str = "File storage operation failed",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, context=context)


class LLMServiceError(ScribeSnapError):
    """
    Raised when the LLM (Gemini) service fails after all retries.
    
    What:    Gemini API returned an error or timed out, and retry logic exhausted.
    When:    After tenacity retries are exhausted (default: 3 attempts with backoff).
    HTTP:    503 Service Unavailable
    
    Why 503 (not 502):
        503 signals that the service is temporarily unavailable and the client
        should retry later. 502 suggests our gateway is broken — but the issue
        is with the upstream Gemini service, not our server.
    
    Response includes:
        - retry_after: Suggested seconds before client retries (from circuit breaker state)
        - Human-readable explanation of what happened
    """

    def __init__(
        self,
        message: str = "AI text extraction service is temporarily unavailable",
        retry_after: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        ctx = context or {}
        if retry_after:
            ctx["retry_after"] = retry_after
        super().__init__(message=message, context=ctx)
        self.retry_after = retry_after


class CircuitBreakerOpenError(ScribeSnapError):
    """
    Raised when the circuit breaker is in OPEN state.
    
    What:    Too many consecutive Gemini failures triggered the circuit breaker.
    When:    After cb_failure_threshold consecutive failures (default: 5).
    HTTP:    503 Service Unavailable
    
    How circuit breaker works:
        CLOSED (normal) → failures increment counter
        → After 5 failures → OPEN (reject all calls for 60 seconds)
        → After 60 seconds → HALF-OPEN (allow one test call)
        → If test succeeds → CLOSED (resume normal operation)
        → If test fails → OPEN again (reset 60-second timer)
    
    Why circuit breaker:
        Without it, when Gemini is down, every request:
        1. Waits for connection timeout (10s)
        2. Retries 3 times with backoff (2s + 4s + 8s waits = 14s)
        3. Total: up to 3 * (10s + timeout) + backoff = ~42s per request
        With circuit breaker, requests fail immediately (<1ms) when circuit is open,
        preserving server resources and giving users instant feedback.
    """

    def __init__(
        self,
        recovery_time: int = 60,
        context: Optional[Dict[str, Any]] = None,
    ):
        message = (
            f"AI service is temporarily unavailable due to repeated failures. "
            f"The service will automatically retry in approximately {recovery_time} seconds."
        )
        ctx = context or {}
        ctx["recovery_time"] = recovery_time
        super().__init__(message=message, context=ctx)
        self.recovery_time = recovery_time


class DatabaseError(ScribeSnapError):
    """
    Raised when database operations fail unexpectedly.
    
    What:    A database query, insert, or update failed.
    When:    Connection lost mid-query, constraint violation, deadlock, etc.
    HTTP:    500 Internal Server Error
    
    Security Note:
        The message returned to the client is always generic.
        Detailed error info (SQL query, constraint name, etc.) is logged
        server-side only — never exposed to the API consumer.
        Why: Detailed DB errors could reveal schema, table names, or data
        that an attacker could exploit.
    """

    def __init__(
        self,
        message: str = "A database error occurred. Please try again later.",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, context=context)


class RateLimitExceededError(ScribeSnapError):
    """
    Raised when a client exceeds the per-IP request rate limit.
    
    What:    Client sent too many requests within the rate limit window.
    When:    After rate_limit_requests (default: 100) in rate_limit_window (default: 1 hour).
    HTTP:    429 Too Many Requests
    
    Response includes:
        - retry_after: Seconds until the rate limit window resets
        - Retry-After header for HTTP-compliant clients
    """

    def __init__(
        self,
        retry_after: int = 60,
        context: Optional[Dict[str, Any]] = None,
    ):
        message = (
            f"Rate limit exceeded. Please wait {retry_after} seconds before making more requests."
        )
        ctx = context or {}
        ctx["retry_after"] = retry_after
        super().__init__(message=message, context=ctx)
        self.retry_after = retry_after
