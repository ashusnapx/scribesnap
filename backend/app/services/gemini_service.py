"""
ScribeSnap Backend — Google Gemini Service Implementation
==========================================================

What:  Concrete LLM service using Google Gemini Vision API for handwriting recognition.
Why:   Gemini offers free tier access and strong vision capabilities for text extraction.
How:   Sends image + optimized prompt to Gemini, receives extracted text, with
       comprehensive retry logic, circuit breaker, and performance monitoring.
Who:   Instantiated once at app startup; called by NoteService for each parse request.
When:  After image validation and storage, before database persistence.

Resilience Strategy:
    1. Tenacity retry with exponential backoff + jitter for transient failures
    2. Circuit breaker to protect against cascade failures when Gemini is down
    3. Timeout handling for both connection and response phases
    4. Detailed logging for debugging and performance monitoring

Why Google Gemini:
    - Free tier: 15 requests/minute, 1 million tokens/day (sufficient for dev/small scale)
    - Strong vision: Handles diverse handwriting styles, including cursive
    - Fast: gemini-1.5-flash typically responds in 2-5 seconds
    Alternative considered: GPT-4V (better accuracy but expensive), Tesseract (free but poor
    handwriting accuracy — designed for printed text)
"""

import logging
import time
import uuid
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)

from app.config import settings
from app.exceptions import LLMServiceError, CircuitBreakerOpenError
from app.services.llm_base import LLMService

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
# Circuit Breaker Implementation
# ══════════════════════════════════════════════════════════════════════════

class CircuitBreaker:
    """
    Implements the circuit breaker pattern to prevent cascade failures.
    
    State Machine:
        CLOSED (normal operation)
            → On failure: increment failure_count
            → When failure_count >= threshold: transition to OPEN
        
        OPEN (rejecting all requests)
            → All calls raise CircuitBreakerOpenError immediately
            → After recovery_timeout seconds: transition to HALF_OPEN
        
        HALF_OPEN (testing recovery)
            → Allow ONE request through
            → On success: transition to CLOSED (reset failure_count)
            → On failure: transition back to OPEN (reset timer)
    
    Why this pattern:
        Without circuit breaker, when Gemini is down:
        - Each request waits 10s (connect timeout) × 3 retries = 30s minimum
        - Server threads are blocked, unable to serve other requests
        - User sees a long loading spinner, then an error
        
        With circuit breaker:
        - After 5 failures, subsequent requests fail instantly (<1ms)
        - Users get immediate feedback: "Service temporarily unavailable"
        - Server resources are freed for other operations
        - Gemini gets breathing room to recover
    
    Thread Safety:
        This implementation is NOT thread-safe (uses simple counters).
        For production with multiple workers, use Redis-backed circuit breaker.
        Why acceptable for now: uvicorn async workers share a single process.
    """

    # Circuit breaker states
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Rejecting all requests
    HALF_OPEN = "half_open"  # Testing if service recovered

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """
        Args:
            failure_threshold: Consecutive failures before opening circuit
            recovery_timeout: Seconds to wait before testing recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = self.CLOSED
        self.last_failure_time: Optional[float] = None
        # Why track last_failure_time: Used to calculate when OPEN → HALF_OPEN transition occurs

    def can_execute(self) -> bool:
        """
        Check if a request is allowed through the circuit breaker.
        
        Returns:
            True if the request can proceed (CLOSED or HALF_OPEN after timeout).
        
        Raises:
            CircuitBreakerOpenError if circuit is OPEN and recovery timeout hasn't elapsed.
        """
        if self.state == self.CLOSED:
            return True

        if self.state == self.OPEN:
            # Check if enough time has passed to test recovery
            elapsed = time.time() - (self.last_failure_time or 0)
            if elapsed >= self.recovery_timeout:
                # Transition: OPEN → HALF_OPEN (allow one test request)
                logger.info(
                    "Circuit breaker transitioning to HALF_OPEN after %.1fs",
                    elapsed,
                )
                self.state = self.HALF_OPEN
                return True
            else:
                # Still in recovery period — reject immediately
                remaining = int(self.recovery_timeout - elapsed)
                raise CircuitBreakerOpenError(recovery_time=remaining)

        # HALF_OPEN: allow the test request through
        return True

    def record_success(self) -> None:
        """
        Record a successful API call. Resets the circuit breaker to CLOSED.
        
        When called from HALF_OPEN state, this means the service has recovered.
        """
        if self.state == self.HALF_OPEN:
            logger.info("Circuit breaker transitioning to CLOSED (service recovered)")
        self.failure_count = 0
        self.state = self.CLOSED
        self.last_failure_time = None

    def record_failure(self) -> None:
        """
        Record a failed API call. May trigger CLOSED → OPEN transition.
        """
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == self.HALF_OPEN:
            # Test request failed — back to OPEN
            logger.warning(
                "Circuit breaker returning to OPEN (test request failed)"
            )
            self.state = self.OPEN
        elif self.failure_count >= self.failure_threshold:
            # Too many consecutive failures — open the circuit
            logger.warning(
                "Circuit breaker OPENING after %d consecutive failures",
                self.failure_count,
            )
            self.state = self.OPEN


# ══════════════════════════════════════════════════════════════════════════
# Gemini Service
# ══════════════════════════════════════════════════════════════════════════

class GeminiService(LLMService):
    """
    Google Gemini Vision API implementation for handwriting text extraction.
    
    Architecture:
        - Singleton instance created at app startup
        - Configures Gemini SDK with API key
        - Uses optimized prompt for handwriting recognition
        - Wraps all calls with retry logic and circuit breaker
    
    Error Handling Chain:
        API call fails → tenacity retries (3 attempts with backoff)
        → All retries fail → record circuit breaker failure
        → Circuit breaker threshold reached → future calls rejected instantly
        → Circuit breaker recovery timeout → allow test call (HALF_OPEN)
        → Test succeeds → resume normal operation (CLOSED)
    """

    # Why this prompt: Optimized through experimentation to handle:
    # - Multiple handwriting styles (print, cursive, mixed)
    # - Various image qualities (camera phone, scanner, whiteboard)
    # - Mathematical notation and special characters
    # - Preserving paragraph structure and line breaks
    PARSE_PROMPT = """You are an expert handwriting recognition system. Analyze this image 
and extract ALL handwritten text with high accuracy.

Instructions:
1. Preserve the original text structure (paragraphs, line breaks, bullet points)
2. If text is unclear, provide your best interpretation with [unclear] markers
3. Maintain any numbering, bullets, or list formatting
4. Preserve mathematical notation if present
5. Return ONLY the extracted text — no commentary, explanations, or descriptions of the image
6. If no handwritten text is found, return "No handwritten text detected in the image."

Extract the handwritten text from this image:"""

    def __init__(self):
        """
        Initialize Gemini service with API key and model configuration.
        
        Why configure here (not per-request):
            - API key doesn't change during runtime
            - Model object is reusable across requests (thread-safe)
            - Avoids re-initialization overhead per request
        """
        # Configure the Gemini SDK with our API key
        # Why global configure: The SDK uses module-level state for auth
        if settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here":
            genai.configure(api_key=settings.gemini_api_key)

        # Create the generative model instance
        # Why store as instance var: Reused across all parse_image calls
        self.model = genai.GenerativeModel(settings.gemini_model)

        # Initialize circuit breaker with configured thresholds
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.cb_failure_threshold,
            recovery_timeout=settings.cb_recovery_timeout,
        )

        logger.info(
            "GeminiService initialized with model=%s, "
            "circuit_breaker(threshold=%d, recovery=%ds)",
            settings.gemini_model,
            settings.cb_failure_threshold,
            settings.cb_recovery_timeout,
        )

    async def parse_image(self, image_path: str) -> str:
        """
        Extract handwritten text from an image using Gemini Vision API.
        
        What:    Sends image to Gemini with optimized handwriting prompt.
        Who:     Called by NoteService.parse_note() during upload workflow.
        When:    After file validation and storage, before DB persistence.
        
        Flow:
            1. Check circuit breaker → may raise CircuitBreakerOpenError
            2. Read image from disk (validated by FileService already)
            3. Send to Gemini with retry logic (3 attempts, exponential backoff)
            4. Record success/failure in circuit breaker
            5. Return extracted text
        
        Args:
            image_path: Absolute path to the image file.
        
        Returns:
            Extracted text as string. Empty string if no text detected.
        
        Raises:
            CircuitBreakerOpenError: Circuit is open (too many recent failures)
            LLMServiceError: Gemini failed after all retry attempts
        """
        # Generate a unique request ID for tracing this specific API call
        # Why per-call ID: Enables correlating logs even with concurrent requests
        request_id = str(uuid.uuid4())[:8]

        # Step 1: Check circuit breaker before making the API call
        # Why first: Avoids unnecessary file I/O if we're going to reject anyway
        self.circuit_breaker.can_execute()  # Raises CircuitBreakerOpenError if open

        logger.info(
            "[%s] Starting Gemini parse for image: %s",
            request_id,
            Path(image_path).name,  # Log filename only, not full path (security)
        )

        try:
            # Step 2: Call Gemini with retry logic
            # Why separate method: Tenacity @retry must decorate a standalone function
            result = await self._call_gemini_with_retry(image_path, request_id)

            # Step 3: Record success in circuit breaker
            self.circuit_breaker.record_success()
            return result

        except CircuitBreakerOpenError:
            # Re-raise circuit breaker errors (already handled in can_execute)
            raise
        except RetryError as e:
            # All retry attempts exhausted
            self.circuit_breaker.record_failure()
            logger.error(
                "[%s] All Gemini retries exhausted: %s",
                request_id,
                str(e.last_attempt.exception()) if e.last_attempt else "Unknown error",
            )
            raise LLMServiceError(
                message="AI text extraction failed after multiple attempts. Please try again later.",
                retry_after=self.circuit_breaker.recovery_timeout,
                context={"request_id": request_id, "attempts": settings.retry_max_attempts},
            )
        except Exception as e:
            # Unexpected error — still record in circuit breaker
            self.circuit_breaker.record_failure()
            logger.error(
                "[%s] Unexpected Gemini error: %s",
                request_id,
                str(e),
                exc_info=True,
            )
            raise LLMServiceError(
                message="An unexpected error occurred during text extraction.",
                context={"request_id": request_id, "error_type": type(e).__name__},
            )

    @retry(
        # What: Retry on transient errors that may resolve on their own
        # Why these types: Network issues and rate limits are transient
        retry=retry_if_exception_type((
            ConnectionError,
            TimeoutError,
            Exception,  # Gemini SDK raises generic exceptions for API errors
        )),
        # What: Stop after N attempts (default: 3)
        stop=stop_after_attempt(settings.retry_max_attempts),
        # What: Exponential backoff with jitter
        # How: wait = min(max_wait, min_wait * 2^attempt) + random(0, 1)
        # Why jitter: Prevents thundering herd when multiple workers retry simultaneously
        # Example: attempt 1 → ~2s, attempt 2 → ~4s, attempt 3 → ~8s (+jitter)
        wait=wait_exponential_jitter(
            initial=settings.retry_min_wait,
            max=settings.retry_max_wait,
            jitter=1,  # Add 0-1 seconds of random jitter
        ),
        # What: Log each retry attempt for debugging
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _call_gemini_with_retry(self, image_path: str, request_id: str) -> str:
        """
        Internal method: Makes the actual Gemini API call with retry decoration.
        
        Why separate from parse_image:
            Tenacity's @retry decorator wraps the entire function. If we put
            retry logic on parse_image(), circuit breaker checks would also retry,
            which we don't want. This separation gives us precise control over
            what gets retried (only the API call) vs what doesn't (circuit breaker).
        
        Performance tracking:
            We log duration and response size for each call to enable:
            - Latency monitoring and SLA compliance
            - Identifying slow images (large, complex handwriting)
            - Cost estimation based on token usage patterns
        """
        start_time = time.time()

        try:
            # Upload image to Gemini (supports local file paths)
            # Why upload_file: Gemini requires image data, not just a URL
            # The SDK handles encoding and transmission
            image_file = genai.upload_file(path=image_path)

            # Send image + prompt to Gemini for text extraction
            # Why generate_content (not chat): Single-turn extraction, no conversation needed
            response = await self.model.generate_content_async(
                [self.PARSE_PROMPT, image_file],
                request_options={"timeout": 60},  # 60s timeout for response
            )

            # Calculate latency for monitoring
            duration_ms = (time.time() - start_time) * 1000

            # Extract text from response
            # Why .text: Gemini returns a structured response; .text gives plain text
            extracted_text = response.text.strip() if response.text else ""

            logger.info(
                "[%s] Gemini parse completed in %.0fms, extracted %d chars",
                request_id,
                duration_ms,
                len(extracted_text),
            )

            return extracted_text

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning(
                "[%s] Gemini API call failed after %.0fms: %s",
                request_id,
                duration_ms,
                str(e),
            )
            raise  # Let tenacity handle the retry

    async def health_check(self) -> bool:
        """
        Check if Gemini API is reachable.
        
        What:    Verifies API key validity and service availability.
        How:     Lists available models (lightweight API call, no token cost).
        Returns: True if reachable and authenticated, False otherwise.
        
        Why not send a test image:
            - Would consume API quota unnecessarily
            - list_models is free and sufficient to verify connectivity + auth
        """
        try:
            # List models to verify API key and connectivity
            # This is a lightweight call that doesn't consume tokens
            models = genai.list_models()
            # Check if our configured model exists
            model_names = [m.name for m in models]
            target = f"models/{settings.gemini_model}"
            if target in model_names:
                return True
            logger.warning("Configured model %s not found in available models", target)
            return True  # API is reachable even if model name is different
        except Exception as e:
            logger.warning("Gemini health check failed: %s", str(e))
            return False


# ── Singleton Instance ────────────────────────────────────────────────────
# Why singleton: GeminiService holds the circuit breaker state, which must be
# shared across all requests. Creating a new instance per request would reset
# the circuit breaker (defeating its purpose).
gemini_service = GeminiService()
