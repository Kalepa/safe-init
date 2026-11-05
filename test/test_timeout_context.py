import threading
import time
from contextvars import Context, ContextVar
from functools import wraps
from unittest.mock import Mock

import pytest
from awslambdaric.lambda_context import LambdaContext
from structlog.testing import CapturingLogger

from safe_init.decorator import safe_wrapper
from safe_init.errors import SafeInitTimeoutWarning
from safe_init.safe_logging import get_logger
from safe_init.slack import get_slack_webhook_url


# --- Test context isolation helper ---
def _with_fresh_context(test):
    """Keep named overrides leaked by other tests out of these invocations."""

    @wraps(test)
    def wrapped(*args, **kwargs):
        return Context().run(test, *args, **kwargs)

    return wrapped


# --- End test context isolation helper ---


@pytest.mark.parametrize("use_context", [True, False])
@_with_fresh_context
def test_timeout_notifications_keep_context_across_warm_invocations(monkeypatch, use_context):
    """Documented initialization overrides must also reach timeout notifications."""
    monkeypatch.setenv("SAFE_INIT_NO_DATADOG_WRAPPER", "true")
    monkeypatch.setenv("SAFE_INIT_NOTIFY_SEC_BEFORE_TIMEOUT", "10")
    monkeypatch.delenv("SAFE_INIT_SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("SAFE_INIT_DLQ", raising=False)
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    post = Mock(return_value=Mock(status_code=200))
    monkeypatch.setattr("requests.post", post)
    finished = threading.Event()
    warnings = []

    def record_timeout(args):
        warnings.append(args.exc_value)
        finished.set()

    monkeypatch.setattr(threading, "excepthook", record_timeout)
    webhook = ContextVar("safe_init_slack_webhook_url")
    logger_getter = ContextVar("safe_init_logger_getter")
    result = {"completed": True}

    @safe_wrapper
    def handler(event, context):
        assert finished.wait(5), "timeout thread did not finish"
        return result

    for invocation in range(2):
        finished.clear()
        logger = CapturingLogger()
        url = f"https://example.invalid/timeout-{invocation}"
        webhook_token = webhook.set(url if use_context else None)

        def getter(logger=logger):
            return logger

        logger_token = logger_getter.set(getter if use_context else None)
        if not use_context:
            monkeypatch.setenv("SAFE_INIT_SLACK_WEBHOOK_URL", url)
        context = LambdaContext(f"request-{invocation}", None, None, int(time.time() * 1000) + 1000)
        context.function_name = "context-test"
        try:
            assert get_slack_webhook_url() == url
            if use_context:
                assert get_logger() is logger
            assert handler({}, context) is result
            handler.timeout_thread.join(5)
            assert not handler.timeout_thread.is_alive()
            assert webhook.get() == (url if use_context else None)
            assert logger_getter.get() is (getter if use_context else None)
        finally:
            webhook.reset(webhook_token)
            logger_getter.reset(logger_token)

        assert len(warnings) == invocation + 1
        assert isinstance(warnings[-1], SafeInitTimeoutWarning)
        assert post.call_count == invocation + 1, "configured timeout Slack notification was dropped"
        assert post.call_args.args == (url,)
        assert f"request-{invocation}" in str(post.call_args.kwargs["json"])
        if use_context:
            assert any(
                call.method_name == "error" and "Impending Lambda execution timeout" in call.args[0]
                for call in logger.calls
            ), "timeout did not use the configured logger"


@pytest.mark.parametrize("handler_raises", [False, True])
@_with_fresh_context
def test_timeout_cancellation_preserves_handler_outcome(monkeypatch, handler_raises):
    """Context propagation must preserve cancellation after success or failure."""
    monkeypatch.setenv("SAFE_INIT_NO_DATADOG_WRAPPER", "true")
    monkeypatch.setenv("SAFE_INIT_NOTIFY_SEC_BEFORE_TIMEOUT", "1")
    monkeypatch.setenv("SAFE_INIT_NO_SLACK_TIMEOUT_NOTIFICATIONS", "true")
    monkeypatch.delenv("SAFE_INIT_DLQ", raising=False)
    logger = CapturingLogger()
    logger_getter = ContextVar("safe_init_logger_getter")
    logger_token = logger_getter.set(lambda: logger)
    warnings = []
    monkeypatch.setattr(threading, "excepthook", lambda args: warnings.append(args.exc_value))
    result = {"completed": True}
    error = ValueError("handler failure")

    @safe_wrapper
    def handler(event, context):
        if handler_raises:
            raise error
        return result

    context = LambdaContext("cancelled-request", None, None, int(time.time() * 1000) + 60000)
    context.function_name = "context-test"
    try:
        if handler_raises:
            with pytest.raises(ValueError) as caught:
                handler({}, context)
            assert caught.value is error
        else:
            assert handler({}, context) is result
        handler.timeout_thread.join(5)
        assert not handler.timeout_thread.is_alive()
        assert not warnings
        assert not any(
            call.method_name == "error" and "Impending Lambda execution timeout" in call.args[0]
            for call in logger.calls
        )
    finally:
        logger_getter.reset(logger_token)
