# Routes package init
"""
ScribeSnap Backend — API Routes Package
=========================================

What:  HTTP route handlers that accept requests and return responses.
Why:   Routes are the entry point for all API calls from the frontend.
How:   Each route module handles a specific resource or action.

Route Inventory:
    - parse.py:   POST /api/parse           (upload and process image)
    - notes.py:   GET  /api/notes            (list notes with pagination)
                  GET  /api/notes/{id}       (get single note detail)
    - health.py:  GET  /health               (service health check)

Design Principle:
    Routes should be THIN — they handle HTTP concerns only:
    - Extract data from request (query params, body, files)
    - Call the appropriate service
    - Format the response with correct status code and headers
    
    Business logic belongs in services, not routes.
    This enables testing services without HTTP overhead.
"""
