"""
This module provides functions for capturing and logging exceptions with Sentry.
"""

import json
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


def sentry_capture(
    e: Exception,
    *,
    fingerprint: list[Any] | None = None,
    tags: dict[str, str] | None = None,
    attachments: dict[str, Any] | None = None,
) -> bool:
    """
    Captures the given exception with Sentry and returns True if successful.
    If Sentry is not installed or initialization fails, logs a warning and returns False.

    :param e: The exception to capture.
    :param fingerprint: A list of strings to group similar exceptions together.
    :param tags: A dictionary of tags to attach to the event.
    :param attachments: A dictionary of attachments to attach to the event. Values must be JSON-serializable.
    :return: True if the exception was successfully captured, False otherwise.
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
                if tags:
                    for key, value in tags.items():
                        scope.set_tag(key, value)
                if attachments:
                    for key, value in attachments.items():
                        try:
                            json_value = json.dumps(value)
                        except TypeError:
                            log_warning("Failed to serialize attachment to JSON, skipping", key=key)
                            continue
                        scope.add_attachment(
                            filename=f"{key}.json",
                            bytes=json_value.encode(),
                            content_type="application/json",
                        )
                sentry_sdk.capture_exception(e)
            return True  # noqa: TRY300
        except Exception:
            log_warning("Failed to capture exception in Sentry", exc_info=True)
    else:
        log_warning("Sentry is not installed")

    return False
