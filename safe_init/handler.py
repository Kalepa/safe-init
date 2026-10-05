"""
This module provides a function for wrapping a Lambda handler function with error handling and logging.
"""

import hashlib
import json
import os
from collections.abc import Callable, Mapping
from functools import wraps
from importlib import import_module
from typing import Any

from safe_init.decorator import safe_wrapper
from safe_init.dlq import SafeInitDummyHandler, context_has_dlq
from safe_init.environment import has_extra_env_vars, load_extra_env_vars
from safe_init.errors import (
    SafeInitError,
    SafeInitInitPhaseTimeoutWarning,
    SafeInitMissingSentryWarning,
)
from safe_init.safe_logging import log_debug, log_exception, log_warning
from safe_init.secrets import (
    context_has_secrets_to_resolve,
    reset_clients,
    resolve_secrets,
)
from safe_init.sentry import sentry_capture
from safe_init.slack import slack_notify
from safe_init.utils import bool_env, env, get_sentry_sdk


def env_wrapped(func: Callable, env_vars: Mapping[str, str | None]) -> Callable:
    """
    Wraps the given function with the given environment variables.

    Args:
        func (Callable): The function to wrap.
        env_vars (Mapping[str, str | None]): The environment variables to wrap the function with.

    Returns:
        The wrapped function.
    """

    @wraps(func)
    def _wrapped(*args, **kwargs) -> Any:  # type: ignore[no-untyped-def] # noqa: ANN002, ANN401
        with env(env_vars):
            return func(*args, **kwargs)

    return _wrapped


def _refresh_secrets_after_restore(
    func: Callable,
    env_vars: dict[str, str | None],
    extra_env_vars: Mapping[str, str | None],
) -> Callable:
    """
    Resolves the secrets again in the first invocation after a SnapStart restore.

    SnapStart runs the initialization once, when Lambda publishes the version, and every restored execution
    environment starts with the secrets resolved at that time. This wrapper resolves them again, so a changed secret
    reaches the function as fast as it does without SnapStart. For every other initialization type it returns `func`
    unchanged.

    The after-restore hook only sets a flag and drops the cached clients, so it adds no network call to the restore
    phase, which Lambda limits to 10 seconds. If the new resolution fails, the function keeps the values from the
    snapshot.

    Args:
        func (Callable): The handler function, already wrapped with `env_vars`.
        env_vars (dict[str, str | None]): The environment variables that `func` applies. Updated in place.
        extra_env_vars (Mapping[str, str | None]): The extra environment variables loaded during initialization.

    Returns:
        The wrapped handler function, or `func` itself if the function does not use SnapStart.
    """
    if os.getenv("AWS_LAMBDA_INITIALIZATION_TYPE") != "snap-start":
        return func

    try:
        from snapshot_restore_py import register_after_restore
    except ImportError:
        log_warning("SnapStart is on but snapshot_restore_py is not available, secrets will not be refreshed")
        return func

    restored = False

    def _after_restore() -> None:
        nonlocal restored
        restored = True
        reset_clients()

    register_after_restore(_after_restore)

    @wraps(func)
    def _wrapped(*args, **kwargs) -> Any:  # type: ignore[no-untyped-def] # noqa: ANN002, ANN401
        nonlocal restored
        if restored:
            restored = False
            try:
                env_vars.update({**resolve_secrets(extra_env_vars), **extra_env_vars})
            except Exception as e:
                log_warning(
                    "Failed to refresh secrets after a SnapStart restore, keeping the snapshot values",
                    error=repr(e),
                )
        return func(*args, **kwargs)

    return _wrapped


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

        extra_env_vars: Mapping[str, str | None] = {}
        if has_extra_env_vars():
            extra_env_vars = load_extra_env_vars()  # type: ignore[assignment]
            log_debug("Loaded extra environment variables", extra_env_vars=extra_env_vars)

        secrets_env: Mapping[str, str | None] = {}
        has_secrets = bool_env("SAFE_INIT_RESOLVE_SECRETS") and context_has_secrets_to_resolve(extra_env_vars)
        if has_secrets:
            secrets_env = resolve_secrets(extra_env_vars)

        custom_env = {**secrets_env, **extra_env_vars}

        with env(custom_env):
            _pre_import_hook(target_handler)
            root_module, handler_name = target_handler.rsplit(".", 1)
            handler_module = import_module(".".join(root_module.split("/")))
            _post_import_hook(target_handler)

        wrapped_handler = env_wrapped(getattr(handler_module, handler_name), custom_env)
        if has_secrets:
            wrapped_handler = _refresh_secrets_after_restore(wrapped_handler, custom_env, extra_env_vars)
        exec_result = safe_wrapper(wrapped_handler)

        if not bool_env("SAFE_INIT_NO_DETECT_UNINITIALIZED_SENTRY") and not get_sentry_sdk().Hub.current.client:
            msg = "Detected missing Sentry initialization"
            slack_notify(
                msg,
                SafeInitMissingSentryWarning(msg),
                handler_name=target_handler,
                message_title="Sentry detector warning",
            )

        return exec_result  # noqa: TRY300
    except Exception as e:
        sentry_result = sentry_capture(e, tags={"handler": target_handler})
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
    if bool_env("SAFE_INIT_NO_DETECT_INIT_ISSUES"):
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
    if bool_env("SAFE_INIT_NOTIFY_SLACK_ON_INIT_ISSUES"):
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
    if bool_env("SAFE_INIT_NO_DETECT_INIT_ISSUES"):
        return
    execution_hash = _get_execution_hash()
    if not os.path.exists(f"/tmp/{__name__}__{execution_hash}__imported__"):
        with open(f"/tmp/{__name__}__{execution_hash}__imported__", "w") as f:
            f.write("OK")
        return


handler = _init_handler()
