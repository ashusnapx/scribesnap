"""
ScribeSnap Backend — Request ID Middleware
============================================

What:  Generates a unique UUID for each incoming request and adds it to the response.
Why:   Enables end-to-end request tracing across all services and log entries.
How:   Creates UUID, injects into request state and logger context, returns in header.
Who:   Applied to every request via Starlette middleware.
When:  First middleware in the chain (runs before all other processing).

Why Request IDs matter:
    Without request IDs, debugging production issues requires:
    - Matching timestamps across logs (imprecise)
    - Guessing which log entries belong to which request (error-prone)
    
    With request IDs:
    - Every log entry from a single request shares the same ID
    - Support can ask users for the request ID from error messages
    - Frontend can include X-Request-ID in error reports for instant correlation
    
    In distributed systems (future), request IDs propagate across services:
    Frontend → Backend (X-Request-ID: abc) → Gemini API (traceable)
"""

import uuid
import logging
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# ── Context Variable ──────────────────────────────────────────────────────
# What: Thread-local (actually coroutine-local) storage for the current request ID
# Why ContextVar: In async Python, multiple requests execute concurrently in the
# same thread. ContextVar ensures each coroutine gets its own request ID value.
# Alternative: threading.local — doesn't work with async (coroutines != threads)
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a unique ID to each request for tracing.
    
    Behavior:
        1. Check if client sent X-Request-ID header (e.g., from frontend)
        2. If present: use it (enables end-to-end tracing from frontend)
        3. If absent: generate a new UUID
        4. Store in ContextVar for use by loggers throughout the request
        5. Add to response headers for client to capture
    
    Why accept client-provided IDs:
        The frontend can generate IDs before the request, associate them with
        user actions, and send them in the header. This enables seamless
        tracing from UI event → API call → log entry.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Use client-provided ID or generate a new one
        # Why short UUID: Full UUID is 36 chars; 8 chars is sufficient for correlation
        # and more readable in logs
        rid = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])

        # Store in ContextVar for access by logger and other middleware
        request_id_var.set(rid)

        # Also store in request.state for access by route handlers
        # Why both: ContextVar for middleware/loggers, request.state for handlers
        request.state.request_id = rid

        # Process the request
        response = await call_next(request)

        # Add request ID to response headers
        # Why: Client can extract this for error reporting and support tickets
        response.headers["X-Request-ID"] = rid

        return response
