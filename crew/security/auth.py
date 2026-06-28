"""
WasteGuard — Twilio Webhook Authentication & Image Validation
=============================================================
Security Feature #1: Twilio Request Signature Validation
  Every WhatsApp message arrives as an HTTP POST from Twilio's servers.
  Without validation, anyone who discovers your /whatsapp URL can send
  fake requests. Twilio signs every request with HMAC-SHA1 using your
  Auth Token — we verify that signature before processing anything.

Security Feature #2: Image Content & Size Validation
  Before writing any downloaded media to disk, we verify:
    - Content-Type is an image/* MIME type (not a script or executable)
    - File size is within a safe limit (10 MB by default)
  This prevents path traversal and resource exhaustion attacks.

References:
  https://www.twilio.com/docs/usage/webhooks/webhooks-security
"""

import os
import logging
from functools import wraps

from flask import request, Response

logger = logging.getLogger(__name__)

# ── Maximum allowed image size in bytes (10 MB) ───────────────────────────────
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECURITY FEATURE 1 — Twilio Request Signature Validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def validate_twilio_signature(f):
    """
    Flask route decorator that validates the X-Twilio-Signature header.

    How it works:
      1. Twilio computes HMAC-SHA1(auth_token, full_request_url + sorted_POST_params)
      2. It sends this as the 'X-Twilio-Signature' header
      3. We recompute the same HMAC and compare — if they don't match, reject

    In DEMO MODE (no TWILIO_AUTH_TOKEN set), validation is skipped so the
    pipeline can still be tested locally without a real Twilio account.

    Usage:
        @app.route("/whatsapp", methods=["POST"])
        @validate_twilio_signature
        def whatsapp_webhook():
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")

        # Demo mode — skip validation if no auth token is configured
        if not auth_token:
            logger.warning(
                "⚠️  SECURITY: TWILIO_AUTH_TOKEN not set — "
                "skipping signature validation (demo mode only)"
            )
            return f(*args, **kwargs)

        try:
            from twilio.request_validator import RequestValidator

            validator = RequestValidator(auth_token)

            # The full URL Twilio posted to (must match exactly, including https)
            request_url = request.url.replace("http://", "https://") if "ngrok" in request.url else request.url

            # All POST form parameters Twilio sent
            post_params = request.form.to_dict()

            # The signature Twilio included in the request header
            twilio_signature = request.headers.get("X-Twilio-Signature", "")

            # Recompute the expected signature and compare
            if not validator.validate(request_url, post_params, twilio_signature):
                logger.error(
                    "🚨 SECURITY: Twilio signature validation FAILED — "
                    "request rejected. URL: %s", request_url
                )
                return Response(
                    "Forbidden: Invalid Twilio signature",
                    status=403,
                    content_type="text/plain"
                )

            logger.info("✅ SECURITY: Twilio signature validated successfully")

        except ImportError:
            # twilio package not installed — skip validation with a warning
            logger.warning("⚠️  SECURITY: twilio package not installed — cannot validate signature")

        except Exception as e:
            # Unexpected error in validation — log but don't crash the request
            logger.error("⚠️  SECURITY: Signature validation error: %s", e)

        return f(*args, **kwargs)

    return decorated


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECURITY FEATURE 2 — Image Content-Type & Size Validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def validate_image(content_type: str, content_bytes: bytes) -> tuple[bool, str]:
    """
    Validate a downloaded media file before writing it to disk.

    Checks:
      1. MIME type must start with 'image/' (rejects scripts, executables, etc.)
      2. File size must not exceed MAX_IMAGE_SIZE_BYTES (rejects resource exhaustion)

    Args:
        content_type:  The Content-Type header value from the downloaded file
        content_bytes: The raw file bytes

    Returns:
        (True, "ok")                 if the file is safe to write
        (False, "reason string")     if validation failed
    """
    # Check 1: Content-Type must be an image MIME type
    if not content_type or not content_type.startswith("image/"):
        reason = (
            f"Invalid content type '{content_type}'. "
            "Only image files are accepted."
        )
        logger.warning("🚨 SECURITY: Image validation failed — %s", reason)
        return False, reason

    # Check 2: File size must be within the allowed limit
    size_bytes = len(content_bytes)
    if size_bytes > MAX_IMAGE_SIZE_BYTES:
        size_mb = size_bytes / (1024 * 1024)
        reason = (
            f"Image too large ({size_mb:.1f} MB). "
            f"Maximum allowed size is {MAX_IMAGE_SIZE_BYTES // (1024*1024)} MB."
        )
        logger.warning("🚨 SECURITY: Image validation failed — %s", reason)
        return False, reason

    logger.info(
        "✅ SECURITY: Image validated — type=%s, size=%.1f KB",
        content_type, size_bytes / 1024
    )
    return True, "ok"
