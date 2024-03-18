"""
Based on https://github.com/getsentry/sentry-python/blob/46c24ea70a47ced2411f9d69ffccb9d2dc8f3e1d/sentry_sdk/utils.py
"""

import os
import threading
import time
from typing import Any

from safe_init import tracer
from safe_init.dlq import context_has_dlq, preload_sqs_client, push_event_to_dlq
from safe_init.errors import SafeInitTimeoutWarning
from safe_init.safe_logging import (
    get_logger,
    log_debug,
    log_error,
    log_exception,
    log_warning,
)
from safe_init.sentry import sentry_capture
from safe_init.slack import slack_notify
from safe_init.utils import aggregate_traced_fn_calls, format_traces, is_lambda_handler


# We don't want to fail if the ddtrace patcher is not available, so we just
# define a dummy function.
def _dummy_patch(*args, **kwargs) -> None:  # type: ignore[no-untyped-def] # noqa: ARG001, ANN002
    log_warning("ddtrace `patch` is not available, doing nothing")


if os.getenv("SAFE_INIT_NO_DATADOG_WRAPPER") is not None:
    patch = _dummy_patch
else:
    try:
        from ddtrace import patch as _raw_ddtrace_patch

        def _safe_ddtrace_patch(*args, **kwargs) -> None:  # type: ignore[no-untyped-def] # noqa: ANN002
            try:
                _raw_ddtrace_patch(*args, **kwargs)
            except Exception:
                log_exception("Failed to execute ddtrace patch, proceeding anyway")

        patch = _safe_ddtrace_patch
    except Exception:
        log_exception("Failed to import ddtrace patcher")
        patch = _dummy_patch


class TimeoutThread(threading.Thread):
    """
    Creates a Thread which runs (sleeps) for a time duration equal to
    waiting_time and then raises a custom SafeInitTimeoutWarning exception.
    """

    def __init__(
        self,
        waiting_time: float,
        timeout_message: str,
        call_args: tuple[Any, ...],
        call_kwargs: dict[str, Any],
        execution_fingerprint: list[Any],
    ) -> None:
        threading.Thread.__init__(self)
        self.waiting_time = waiting_time
        self.timeout_message = timeout_message
        self.call_args = call_args
        self.call_kwargs = call_kwargs
        self.execution_fingerprint = execution_fingerprint
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        # Save the thread start time
        thread_start_time = time.time()
        log_debug("Timeout thread started", waiting_time=self.waiting_time, start_time=thread_start_time)

        # Execute ddtrace's patching in case preloading writes something to logs
        patch(logging=True)

        # Preload as much as possible to make timeout actions faster
        try:
            preload_sqs_client()
            get_logger()
        except Exception as e:
            log_warning("Preloading failed in the timeout thread, proceeding anyway", exc_info=e)

        # Subtract the time spent in preloading from waiting time, then schedule the action
        actual_waiting_time = self.waiting_time - (time.time() - thread_start_time)
        log_debug("Timeout thread waiting", actual_waiting_time=actual_waiting_time)
        self._stop_event.wait(actual_waiting_time)

        log_debug("Timeout thread finished waiting")
        if self._stop_event.is_set():
            log_debug("Timeout thread was stopped")
            return

        log_debug("Timeout thread processing data before raising")

        if context_has_dlq():
            log_debug("Pushing to DLQ")
            push_event_to_dlq(*self.call_args, **self.call_kwargs)
            log_debug("Pushed to DLQ")

        calls_by_time = []

        # Check if execution was traced to optionally include the trace in timeout warnings
        if is_lambda_handler(self.call_args):
            log_debug("Checking for traces")
            if tracer.is_traced():
                log_debug("Tracer is active")
                fn_calls = tracer.get_function_calls()
                aggregated_calls = aggregate_traced_fn_calls(fn_calls)
                log_debug("Got aggregated calls", aggregated_calls=aggregated_calls)
                calls_by_time = sorted(aggregated_calls, key=lambda x: x[2], reverse=True)
                log_debug("Sorted calls by time", calls_by_time=calls_by_time)

        exc = SafeInitTimeoutWarning(self.timeout_message)
        exc.traces = calls_by_time

        sentry_result = sentry_capture(exc, fingerprint=self.execution_fingerprint)
        log_debug("Sentry capture result", sentry_capture_result=sentry_result)
        log_error(
            self.timeout_message,
            sentry_capture_result=sentry_result,
            longest_calls=calls_by_time[:40],
        )

        if not os.getenv("SAFE_INIT_NO_SLACK_TIMEOUT_NOTIFICATIONS"):
            slack_notify(
                str(exc),
                exc,
                lambda_context=self.call_args[1] if is_lambda_handler(self.call_args) else None,
                sentry_capture_result=sentry_result,
                additional_context=format_traces(calls_by_time, 15),
            )

        # Write tracing details to logs
        if calls_by_time:
            log_warning("All function call summaries", calls_by_time=calls_by_time)
            log_warning("All function calls", raw_call_list=fn_calls)

        # Save Exception in a private field for tests to assert on
        self._exception = exc

        # Raising Exception after timeout duration is reached
        raise exc
