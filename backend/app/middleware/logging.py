"""
ScribeSnap Backend — Request Logging Middleware
=================================================

What:  Structured JSON logging for every HTTP request and response.
Why:   Enables monitoring, debugging, alerting, and performance analysis.
How:   Logs request details on arrival, response details on completion,
       includes duration for performance tracking.
Who:   Applied to every request via Starlette middleware.
When:  After RequestIDMiddleware (uses request ID for correlation).

Log Format (JSON):
    {
        "timestamp": "2024-01-15T12:00:00.000Z",
        "level": "INFO",
        "request_id": "a1b2c3d4",
        "method": "POST",
        "path": "/api/parse",
        "status": 201,
        "duration_ms": 3456.78,
        "client_ip": "192.168.1.100",
        "user_agent": "Mozilla/5.0..."
    }

Why JSON logging:
    - Machine-readable: Log aggregation tools (ELK, CloudWatch, Datadog)
      can parse and index fields automatically
    - Structured: Each field is searchable independently
    - Consistent: Same format for all log entries
    Alternative: Human-readable format — easier to read manually but
    impossible to parse reliably at scale

What we log vs what we DON'T log (privacy):
    ✅ Log: method, path, status, duration, IP, user-agent, request ID
    ❌ Don't log: request body (may contain PII), file contents, headers with auth
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.request_id import request_id_var

logger = logging.getLogger("scribesnap.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs structured information about each HTTP request and response.
    
    Logged information:
        - Request: method, path, client IP
        - Response: status code, duration in milliseconds
        - Correlation: request ID from RequestIDMiddleware
    
    Performance tracking:
        Duration is measured from middleware entry to response return.
        This includes all processing time: validation, Gemini API calls,
        database queries, and serialization.
        
        Typical durations:
        - GET /health: 1-5ms
        - GET /api/notes: 10-50ms (database query)
        - POST /api/parse: 2000-8000ms (Gemini API call dominates)
    
    Why not use uvicorn's access log:
        Uvicorn logs basic access info, but:
        1. No request ID correlation
        2. No JSON format (hard to parse at scale)
        3. No duration tracking
        4. Can't be customized per-route
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Capture start time for duration calculation
        # Why time.perf_counter: Higher resolution than time.time() (~100ns vs ~1μs)
        start_time = time.perf_counter()

        # Extract client information
        # Why getattr: request.client may be None in testing
        client_ip = getattr(request.client, "host", "unknown") if request.client else "unknown"
        method = request.method
        path = request.url.path
        rid = request_id_var.get("")

        # Skip logging for health checks (too noisy in production)
        # Why: Health checks run every 10-30 seconds; logging them clutters important logs
        if path == "/health":
            return await call_next(request)

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Choose log level based on status code
        # Why: Different levels enable severity-based alerting
        # 5xx → ERROR (system problem, needs investigation)
        # 4xx → WARNING (client error, may indicate UX issues)
        # 2xx/3xx → INFO (normal operation)
        status = response.status_code
        if status >= 500:
            log_level = logging.ERROR
        elif status >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        logger.log(
            log_level,
            "%s %s %d %.1fms [%s] from %s",
            method,
            path,
            status,
            duration_ms,
            rid,
            client_ip,
            extra={
                "request_id": rid,
                "method": method,
                "path": path,
                "status": status,
                "duration_ms": round(duration_ms, 2),
                "client_ip": client_ip,
            },
        )

        return response
