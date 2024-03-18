"""
This module provides functions for capturing and logging exceptions with Sentry.
"""

import os
from typing import Any

from safe_init.safe_logging import log_warning

USE_SENTRY = False

if os.environ.get("SENTRY_DSN"):
    try:
        import sentry_sdk

        USE_SENTRY = True
    except ImportError:
        pass

if os.environ.get("UNIT_TEST_SENTRY"):
    USE_SENTRY = True


def sentry_capture(e: Exception, *, fingerprint: list[Any] | None = None) -> bool:
    """
    Captures the given exception with Sentry and returns True if successful.
    If Sentry is not installed or initialization fails, logs a warning and returns False.
    """
    if USE_SENTRY:
        try:
            sentry_sdk.init(os.environ.get("SENTRY_DSN", ""), environment=os.environ.get("SAFE_INIT_ENV", "dev"))
        except Exception:
            log_warning("Failed to initialize Sentry", exc_info=True)
            return False

        try:
            with sentry_sdk.push_scope() as scope:
                if fingerprint:
                    scope.fingerprint = fingerprint
                sentry_sdk.capture_exception(e)
            return True  # noqa: TRY300
        except Exception:
            log_warning("Failed to capture exception in Sentry", exc_info=True)
    else:
        log_warning("Sentry is not installed")

    return False
