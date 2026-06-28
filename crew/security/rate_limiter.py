"""
WasteGuard — Per-Number Rate Limiter
=====================================
Security Feature #3: WhatsApp Request Rate Limiting
  Prevents a single resident's number from flooding the pipeline
  (whether accidental or malicious). Each unique sender WhatsApp number
  is tracked in an in-memory sliding window.

Default policy:
  - Max 5 requests per 10-minute window per number
  - After the limit is hit, the user gets a friendly "please wait" reply
    instead of silently processing or dropping

Design notes:
  - Uses a simple in-memory dict (resets on server restart).
  - For production use, replace with Redis for persistence across restarts
    and horizontal scaling.
  - Thread-safe via threading.Lock() since Flask uses threads.
"""

import time
import threading
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
MAX_REQUESTS_PER_WINDOW = 5   # Max allowed requests per phone number
WINDOW_SECONDS          = 600  # Time window in seconds (10 minutes)


class RateLimiter:
    """
    Thread-safe sliding-window rate limiter keyed by WhatsApp phone number.

    Each phone number gets its own deque of request timestamps.
    On each check, timestamps older than WINDOW_SECONDS are evicted,
    then the remaining count is compared to MAX_REQUESTS_PER_WINDOW.

    Example:
        limiter = RateLimiter()
        allowed, wait = limiter.check("+919876543210")
        if not allowed:
            return f"Rate limited. Please wait {wait} seconds."
    """

    def __init__(
        self,
        max_requests: int = MAX_REQUESTS_PER_WINDOW,
        window_seconds: int = WINDOW_SECONDS,
    ):
        # Dict mapping phone_number → deque of request timestamps
        self._requests: dict[str, deque] = defaultdict(deque)

        # Lock ensures thread safety when multiple Flask threads access simultaneously
        self._lock = threading.Lock()

        self.max_requests   = max_requests
        self.window_seconds = window_seconds

    def check(self, phone_number: str) -> tuple[bool, int]:
        """
        Check whether a request from phone_number is within the rate limit.

        Args:
            phone_number: The caller's WhatsApp number (e.g. '+919876543210')

        Returns:
            (True, 0)            — request is allowed
            (False, wait_secs)   — rate limit exceeded; wait_secs until window opens
        """
        now = time.monotonic()

        with self._lock:
            timestamps = self._requests[phone_number]

            # Evict timestamps that have fallen outside the sliding window
            cutoff = now - self.window_seconds
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            # Check if we're at or above the limit
            if len(timestamps) >= self.max_requests:
                # Calculate seconds until the oldest request falls out of window
                oldest_ts  = timestamps[0]
                wait_secs  = int(self.window_seconds - (now - oldest_ts)) + 1

                logger.warning(
                    "🚨 RATE LIMIT: Number %s has made %d requests in the last %ds — "
                    "blocking for %ds",
                    phone_number, len(timestamps), self.window_seconds, wait_secs
                )
                return False, wait_secs

            # Under the limit — record this request timestamp
            timestamps.append(now)

            logger.info(
                "✅ RATE LIMIT: %s — request %d/%d in window",
                phone_number, len(timestamps), self.max_requests
            )
            return True, 0

    def reset(self, phone_number: str):
        """Clear all recorded requests for a number (useful for testing)."""
        with self._lock:
            self._requests[phone_number] = deque()


# ── Module-level singleton — shared across all Flask request threads ──────────
# Import this in app.py with: from crew.security.rate_limiter import limiter
limiter = RateLimiter()
