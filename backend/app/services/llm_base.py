"""
ScribeSnap Backend — Abstract LLM Service Interface
=====================================================

What:  Abstract base class defining the contract for AI text extraction services.
Why:   Abstractions enable swapping providers (Gemini → OpenAI → Anthropic) without
       changing any calling code. This is the Strategy design pattern.
How:   Concrete implementations inherit from LLMService and implement parse_image().
Who:   Called by NoteService during the parse workflow.
When:  After image upload and file validation, before database persistence.

Design Decision:
    Why an abstract class instead of just using GeminiService directly:
    1. Provider flexibility: Today we use Gemini (free tier); tomorrow we might
       switch to GPT-4V or Claude for better accuracy
    2. Testing: We can easily create a MockLLMService for unit tests
    3. Graceful degradation: Could implement a FallbackLLMService that tries
       Gemini first, then falls back to another provider
    4. Configuration-driven: The concrete class can be selected from env vars
    
    Alternative considered: Duck typing (no base class) — works in Python but
    loses IDE support, documentation, and compile-time checking with mypy
"""

from abc import ABC, abstractmethod


class LLMService(ABC):
    """
    Abstract interface for AI-powered text extraction from images.
    
    Contract:
        - parse_image() accepts a file path and returns extracted text
        - Implementations handle their own retry logic and error translation
        - All implementation-specific errors are wrapped in LLMServiceError
        - The caller (NoteService) should not need to know which provider is used
    
    Implementations:
        - GeminiService: Google Gemini Vision API (default, free tier available)
        - (Future) OpenAIService: GPT-4V for potentially higher accuracy
        - (Future) MockLLMService: Returns canned responses for testing
    """

    @abstractmethod
    async def parse_image(self, image_path: str) -> str:
        """
        Extract text from a handwritten note image.
        
        What:    Sends the image to an AI vision model and returns extracted text.
        
        Args:
            image_path: Absolute path to the image file on disk.
                       The file must exist and be a valid image (PNG, JPG, JPEG).
        
        Returns:
            str: The extracted text from the handwritten image.
                 Returns an empty string if no text could be detected.
                 Never returns None — use empty string for "no text found".
        
        Raises:
            LLMServiceError: When the AI service fails after all retries.
                Includes the original error message for logging.
            CircuitBreakerOpenError: When too many consecutive failures have
                occurred and we're protecting the upstream service.
        
        Performance:
            - Typical latency: 2-8 seconds depending on image size and model
            - Retry adds up to 14s in worst case (3 attempts with backoff)
            - Circuit breaker returns instantly when open (<1ms)
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the LLM service is reachable and operational.
        
        What:    Lightweight connectivity test (does NOT consume API quota).
        Who:     Called by the health check endpoint.
        Returns: True if service is reachable, False otherwise.
        """
        ...
