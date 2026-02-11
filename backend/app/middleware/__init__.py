# Middleware package init
"""
ScribeSnap Backend — Middleware Package
========================================

What:  Cross-cutting concerns applied to every request.
Why:   Middleware handles functionality needed across all routes without
       duplicating code in each route handler.

Middleware Chain (order matters!):
    Request → [Rate Limit] → [Request ID] → [Logging] → [CORS] → Route Handler
    
    Why this order:
    1. Rate Limit FIRST: Reject abusive requests before any processing
    2. Request ID: Generate correlation ID for logging and tracing
    3. Logging: Log request details with the generated request ID
    4. CORS: Applied by FastAPI's CORSMiddleware (handles preflight)
    
    The order is reversed for responses:
    Response ← [Rate Limit] ← [Request ID] ← [Logging] ← [CORS] ← Route Handler
    
    This means:
    - Request ID is added to response headers (set during request phase)
    - Logging captures response status and duration (computed at response phase)
"""
