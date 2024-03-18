"""
This module provides a function for wrapping a Lambda handler function with error handling and logging.
"""

import hashlib
import json
import os
from collections.abc import Callable
from importlib import import_module

from safe_init.decorator import safe_wrapper
from safe_init.dlq import SafeInitDummyHandler, context_has_dlq
from safe_init.errors import (
    SafeInitError,
    SafeInitInitPhaseTimeoutWarning,
    SafeInitMissingSentryWarning,
)
from safe_init.safe_logging import log_exception, log_warning
from safe_init.sentry import sentry_capture
from safe_init.slack import slack_notify
from safe_init.utils import get_sentry_sdk


def _init_handler() -> Callable:
    """
    Initializes the Lambda handler function by importing the module and function specified in the SAFE_INIT_HANDLER
    environment variable, and wrapping it with error handling and logging.

    Returns:
        The wrapped Lambda handler function.

    Raises:
        SafeInitError: If the SAFE_INIT_HANDLER environment variable is not set.
        Any other exception raised during initialization.
    """
    try:
        target_handler = os.getenv("SAFE_INIT_HANDLER", "").strip()
        if not target_handler:
            msg = "SAFE_INIT_HANDLER environment variable is not set"
            raise SafeInitError(msg)  # noqa: TRY301

        _pre_import_hook(target_handler)
        root_module, handler_name = target_handler.rsplit(".", 1)
        handler_module = import_module(".".join(root_module.split("/")))
        _post_import_hook(target_handler)

        exec_result = safe_wrapper(getattr(handler_module, handler_name))

        if not os.getenv("SAFE_INIT_NO_DETECT_UNINITIALIZED_SENTRY") and not get_sentry_sdk().Hub.current.client:
            msg = "Detected missing Sentry initialization"
            slack_notify(
                msg,
                SafeInitMissingSentryWarning(msg),
                handler_name=target_handler,
                message_title="Sentry detector warning",
            )

        return exec_result  # noqa: TRY300
    except Exception as e:
        sentry_result = sentry_capture(e)
        msg = (
            "Failed to import handler"
            if isinstance(e, ImportError)
            else "Unexpected error during handler initialization"
        )
        log_exception(msg, sentry_capture_result=sentry_result)
        slack_notify(msg, e, handler_name=target_handler, sentry_capture_result=sentry_result)

        if context_has_dlq():
            return SafeInitDummyHandler(e)

        raise


def _get_execution_hash() -> str:
    """
    Returns a computed execution hash of the Lambda function. This is a naive way of making sure that the code is
    executed in the same context as before (i.e. after the boosted init phase).

    The hash is calculated using the MD5 hash of the contents of the environment variables and the current file path.

    Returns:
        The computed execution hash.
    """
    return hashlib.md5(  # noqa: S324
        (__file__ + json.dumps(dict(sorted(dict(os.environ).items())))).encode("utf-8"),
    ).hexdigest()


def _pre_import_hook(target_handler: str) -> None:
    """
    Runs before the Lambda handler function is imported.

    Args:
        target_handler (str): The target handler function to be imported.
    """
    if os.getenv("SAFE_INIT_NO_DETECT_INIT_ISSUES"):
        return
    execution_hash = _get_execution_hash()
    if os.path.exists(f"/tmp/{__name__}__{execution_hash}__imported__"):
        # The code below is only executed if the import phase is executed after it's already finished executing before.
        # This shouldn't happen, but sometimes it does when the Lambda is warm. Let's log to keep track of such cases.
        msg = "Import hook repeated despite previous successful initialization"
        log_warning(
            msg,
            name=__name__,
            execution_hash=execution_hash,
            env=dict(sorted(dict(os.environ).items())),
        )
        return

    if not os.path.exists(f"/tmp/{__name__}__{execution_hash}__"):
        with open(f"/tmp/{__name__}__{execution_hash}__", "w") as f:
            f.write("OK")
        return

    # The code below is only executed if the code is executed in the same context as before (i.e. after the boosted
    # init phase timed out or failed).
    log_warning(
        "Code is executed in the same context as before",
        execution_hash=execution_hash,
        env=dict(sorted(dict(os.environ).items())),
    )
    if os.getenv("SAFE_INIT_NOTIFY_SLACK_ON_INIT_ISSUES"):
        msg = "Import hook for the Lambda function executed more than once"
        slack_notify(
            msg,
            SafeInitInitPhaseTimeoutWarning(msg),
            handler_name=target_handler,
            message_title="Possible Lambda init phase timeout",
        )


def _post_import_hook(target_handler: str) -> None:  # noqa: ARG001
    """
    Runs after the Lambda handler function is imported.

    Args:
        target_handler (str): The target handler function to be imported.
    """
    if os.getenv("SAFE_INIT_NO_DETECT_INIT_ISSUES"):
        return
    execution_hash = _get_execution_hash()
    if not os.path.exists(f"/tmp/{__name__}__{execution_hash}__imported__"):
        with open(f"/tmp/{__name__}__{execution_hash}__imported__", "w") as f:
            f.write("OK")
        return


handler = _init_handler()
