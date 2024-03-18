"""
The decorator logic is loosely based on the decorator module from the datadog_lambda.wrapper package.
I mention this because I want to give credit where credit is due and also because I don't want to get
sued by Datadog in case this ever sees the light of day.

Also, if this ever breaks, I can always blame Datadog.
"""

import functools
import os
import time
from collections.abc import Callable
from typing import Any, cast

from awslambdaric.lambda_context import LambdaContext

from safe_init import tracer
from safe_init.dlq import context_has_dlq, push_event_to_dlq
from safe_init.safe_logging import log_error, log_exception, log_warning
from safe_init.sentry import sentry_capture
from safe_init.slack import slack_notify
from safe_init.timeout import TimeoutThread
from safe_init.utils import is_lambda_context, is_lambda_handler

if os.getenv("SAFE_INIT_NO_DATADOG_WRAPPER") is None:
    try:
        from datadog_lambda.wrapper import datadog_lambda_wrapper
    except Exception:
        log_exception("Failed to import Datadog wrapper, disabling Datadog integration")

        # We don't want to fail if the Datadog wrapper is not available, so we just
        # define a dummy function.
        def datadog_lambda_wrapper(func: Callable) -> Callable:
            log_error("Datadog wrapper is not available, returning unwrapped function")
            return func


ENV_SAFE_INIT_WRAPPED = "SAFE_INIT_WRAPPED"

NORMAL_NOTIFY_SEC_BEFORE_TIMEOUT = 5
LONG_NOTIFY_SEC_BEFORE_TIMEOUT = 10
LONG_TIMEOUT_THRESHOLD = 120


class _BaseWrapper:
    """
    Base class for function wrappers.
    """

    def __init__(self, func: Callable) -> None:
        """
        Initializes the wrapper with the given function.
        """
        self.func = func

    def __call__(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        """
        Calls the wrapped function with the given arguments and keyword arguments.
        """
        return self.func(*args, **kwargs)


class _SafeWrapper(_BaseWrapper):
    """
    Wrapper that handles exceptions and logs them.
    """

    _force_wrap = False

    def __new__(cls, func: Callable) -> "_SafeWrapper":
        """
        If the wrapper is accidentally applied to the same function multiple times,
        wrap only once.

        If _force_wrap is True, always return a real decorator, useful for unit tests.
        """
        try:
            if cls._force_wrap or not isinstance(func, _SafeWrapper):
                return super().__new__(cls)

            log_warning("Attempted to wrap the same function multiple times")
            return cast(_SafeWrapper, _BaseWrapper(func))
        except Exception:
            log_exception("Failed to wrap function, returning unwrapped")
            return func  # type: ignore[return-value]

    def __init__(self, func: Callable) -> None:
        """
        Initializes the wrapper with the given function and sets the environment variable
        indicating that the function has been wrapped.
        """
        self.func = func
        functools.update_wrapper(self, func)
        self.timeout_thread: TimeoutThread | None = None
        os.environ[ENV_SAFE_INIT_WRAPPED] = "1"

    def __call__(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        """
        Calls the wrapped function with the given arguments and keyword arguments.
        If an exception is raised, logs it and sends a notification to Slack and Sentry.
        """
        try:
            self.stop_timeout_thread()
            self.start_timeout_thread(args, kwargs)

            func = self.func

            if os.getenv("SAFE_INIT_AUTO_TRACE_LAMBDAS", "false").lower() == "true" and is_lambda_handler(args):
                func = tracer.traced(func)

            if os.getenv("SAFE_INIT_NO_DATADOG_WRAPPER") is None and is_lambda_handler(args):
                func = datadog_lambda_wrapper(func)

            return func(*args, **kwargs)
        except Exception as e:
            sentry_result = sentry_capture(e)
            if isinstance(e, ImportError):
                msg = "Runtime import error detected"
            else:
                msg = "Unhandled runtime exception detected"
            log_exception(msg, sentry_capture_result=sentry_result)
            if not sentry_result:
                slack_notify(
                    msg,
                    e,
                    lambda_context=args[1] if is_lambda_handler(args) else None,
                    sentry_capture_result=sentry_result,
                )

            if context_has_dlq():
                push_event_to_dlq(*args, **kwargs)

            raise
        finally:
            self.stop_timeout_thread()

    def start_timeout_thread(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        start_time = time.time() * 1000.0
        if not is_lambda_handler(args) or os.getenv("SAFE_INIT_IGNORE_TIMEOUTS"):
            return

        # If the wrapped function is a Lambda handler, we need to wrap it with a timeout handler
        # to ensure that the function exits before the Lambda timeout. We set the timeout value
        # to 1 second less than the Lambda timeout to ensure that we have enough time to send
        # the notification to Slack and Sentry, and to flush logs to Datadog.
        if not is_lambda_context(args[1]):
            log_error("Second argument is not a LambdaContext, skipping timeout catching", args=args)
            return

        # The LambdaContext class is not available in the runtime environment, so we need to cast
        # the lambda_ctx argument to the external LambdaContext type.
        lambda_ctx = cast(LambdaContext, args[1])

        # The timeout value is the remaining execution time, minus x seconds needed by the thread to gather data and
        # send the notification to Slack, Sentry, and logs.
        current_time = time.time() * 1000.0
        remaining_exec_time = lambda_ctx.get_remaining_time_in_millis() + (current_time - start_time)
        timeout_value = round(remaining_exec_time / 1000)

        notify_sec_before_timeout = int(os.getenv("SAFE_INIT_NOTIFY_SEC_BEFORE_TIMEOUT", "0"))
        if not notify_sec_before_timeout:
            notify_sec_before_timeout = (
                NORMAL_NOTIFY_SEC_BEFORE_TIMEOUT
                if timeout_value < LONG_TIMEOUT_THRESHOLD
                else LONG_NOTIFY_SEC_BEFORE_TIMEOUT
            )

        self.timeout_thread = TimeoutThread(
            remaining_exec_time / 1000.0 - notify_sec_before_timeout,
            timeout_message=(
                f"Impending Lambda execution timeout detected — less than {notify_sec_before_timeout} seconds left to"
                f" configured timeout ({timeout_value}s)"
            ),
            call_args=args,
            call_kwargs=kwargs,
            execution_fingerprint=["TimeoutWarning", lambda_ctx.function_name],
        )

        # Start the thread to raise timeout warning exception
        self.timeout_thread.start()

    def stop_timeout_thread(self) -> None:
        try:
            if self.timeout_thread and self.timeout_thread.is_alive():
                self.timeout_thread.stop()
        except Exception:  # noqa: S110
            # We don't care if this fails, we just want to make sure that the thread is stopped
            pass


safe_wrapper = _SafeWrapper

__all__ = [
    "safe_wrapper",
    "ENV_SAFE_INIT_WRAPPED",
]
