# Services package init
"""
ScribeSnap Backend — Services Layer
=====================================

What:  Business logic layer sitting between routes (HTTP) and database (persistence).
Why:   Separation of concerns — routes handle HTTP, services handle business rules.
How:   Services accept domain objects, apply business logic, and return results.
       They're injected into routes via FastAPI's dependency injection.

Service Inventory:
    - LLMService (abstract): Interface for AI text extraction providers
    - GeminiService: Concrete implementation using Google Gemini Vision API
    - FileService: File upload validation, storage, and cleanup
    - NoteService: Orchestrates upload → validate → parse → persist workflow

Why services are separate from routes:
    1. Testability: Services can be unit-tested without HTTP overhead
    2. Reusability: Same service can be used by different routes or CLI tools
    3. Replaceability: Swap GeminiService for OpenAIService without touching routes
    4. Single responsibility: Routes handle HTTP; services handle logic
"""
