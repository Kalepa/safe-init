import os
import time
import unittest
from unittest.mock import MagicMock, patch

import pytest
from awslambdaric.lambda_context import LambdaContext

from safe_init.decorator import safe_wrapper


class TestSafeWrapper(unittest.TestCase):
    @patch("safe_init.decorator.log_warning")
    def test_safe_wrapper_logs_warning_on_multiple_wraps(self, mock_log_warning):
        @safe_wrapper
        @safe_wrapper
        def my_function():
            return "Hello, world!"

        assert my_function() == "Hello, world!"
        mock_log_warning.assert_called_once_with("Attempted to wrap the same function multiple times")

    @patch("safe_init.decorator.log_exception")
    @patch("safe_init.decorator.sentry_capture")
    def test_safe_wrapper_logs_exception_on_unhandled_exception(self, mock_sentry_capture, mock_log_exception):
        @safe_wrapper
        def my_function():
            raise Exception("Something went wrong")

        mock_sentry_capture.return_value = True

        with pytest.raises(Exception):
            my_function()

        mock_log_exception.assert_called_once_with("Unhandled runtime exception detected", sentry_capture_result=True)

    @patch("safe_init.decorator.log_exception")
    @patch("safe_init.decorator.sentry_capture")
    def test_safe_wrapper_logs_exception_on_import_error(self, mock_sentry_capture, mock_log_exception):
        @safe_wrapper
        def my_function():
            raise ImportError("Failed to import module")

        mock_sentry_capture.return_value = True

        with pytest.raises(ImportError):
            my_function()

        mock_log_exception.assert_called_once_with("Runtime import error detected", sentry_capture_result=True)

    @patch("safe_init.decorator.slack_notify")
    def test_safe_wrapper_notifies_slack_on_exception(self, mock_slack_notify):
        @safe_wrapper
        def my_function(event, context):
            raise Exception("Something went wrong")

        with pytest.raises(Exception):
            my_function({}, MagicMock())

        mock_slack_notify.assert_called_once()

    def test_safe_wrapper_calls_wrapped_function(self):
        @safe_wrapper
        def my_function():
            return "Hello, world!"

        assert my_function() == "Hello, world!"

    @patch("safe_init.decorator.datadog_lambda_wrapper")
    def test_safe_wrapper_calls_wrapped_function_with_datadog(self, mock_datadog_lambda_wrapper):
        @safe_wrapper
        def my_handler(event, context):
            return "Hello, world!"

        mock_datadog_lambda_wrapper.side_effect = lambda x: x

        mock_lambda_context = LambdaContext(
            invoke_id="invoke_id",
            client_context={},
            cognito_identity={},
            epoch_deadline_time_in_ms=int(time.time() * 1000) + 10000,
        )

        assert my_handler({}, mock_lambda_context) == "Hello, world!"
        mock_datadog_lambda_wrapper.assert_called_once()

    @patch("safe_init.decorator.datadog_lambda_wrapper")
    def test_safe_wrapper_calls_wrapped_function_without_datadog(self, mock_datadog_lambda_wrapper):
        @safe_wrapper
        def my_handler(event, context):
            return "Hello, world!"

        os.environ["SAFE_INIT_NO_DATADOG_WRAPPER"] = "1"

        mock_datadog_lambda_wrapper.side_effect = lambda x: x

        mock_lambda_context = LambdaContext(
            invoke_id="invoke_id",
            client_context={},
            cognito_identity={},
            epoch_deadline_time_in_ms=int(time.time() * 1000) + 10000,
        )

        assert my_handler({}, mock_lambda_context) == "Hello, world!"
        mock_datadog_lambda_wrapper.assert_not_called()

    def test_safe_wrapper_catches_exception(self):
        @safe_wrapper
        def my_function():
            raise Exception("Something went wrong")

        with pytest.raises(Exception):
            my_function()

    @patch("safe_init.decorator.push_event_to_dlq")
    @patch("safe_init.decorator.context_has_dlq")
    def test_dlq_handling_on_exception(self, mock_context_has_dlq, mock_push_event_to_dlq):
        mock_context_has_dlq.return_value = True

        @safe_wrapper
        def my_function(event, context):
            raise Exception("Something went wrong")

        with pytest.raises(Exception):
            my_function({}, MagicMock())

        mock_push_event_to_dlq.assert_called_once()

    def test_env_var_already_set(self):
        os.environ["SAFE_INIT_WRAPPED"] = "1"

        @safe_wrapper
        def my_function():
            pass

        # Possibly verify behavior when the env var is already set
        assert os.environ["SAFE_INIT_WRAPPED"] == "1"

    def test_force_wrap_behavior(self):
        # Setting _force_wrap to True for this test
        import safe_init

        safe_init.decorator._SafeWrapper._force_wrap = True

        @safe_wrapper
        @safe_wrapper
        def my_function():
            return "Hello, world!"

        assert my_function() == "Hello, world!"

        # Resetting _force_wrap to its original state
        safe_init.decorator._SafeWrapper._force_wrap = False

    @patch("safe_init.decorator.TimeoutThread")
    def test_timeout_thread_started(self, mock_timeout_thread):
        @safe_wrapper
        def my_handler(event, context):
            pass

        mock_lambda_context = LambdaContext(
            invoke_id="invoke_id",
            client_context={},
            cognito_identity={},
            epoch_deadline_time_in_ms=int(time.time() * 1000) + 10000,
        )

        my_handler({}, mock_lambda_context)
        mock_timeout_thread.assert_called_once()

    def test_timeout_thread_not_started_when_no_context(self):
        @safe_wrapper
        def my_handler(event):
            pass

        my_handler({})
        assert not hasattr(my_handler, "timeout_thread") or my_handler.timeout_thread is None

    def test_timeout_thread_stopped_on_success(self):
        @safe_wrapper
        def my_handler(event, context):
            return "success"

        mock_lambda_context = LambdaContext(
            invoke_id="invoke_id",
            client_context={},
            cognito_identity={},
            epoch_deadline_time_in_ms=int(time.time() * 1000) + 10000,
        )
        my_handler({}, mock_lambda_context)
        _start_time = time.time()
        while my_handler.timeout_thread.is_alive():
            time.sleep(0.1)
            assert time.time() - _start_time < 5
        assert my_handler.timeout_thread is None or not my_handler.timeout_thread.is_alive()

    @patch.dict(os.environ, {"SAFE_INIT_AUTO_TRACE_LAMBDAS": "true"})
    @patch("safe_init.tracer.traced")
    def test_safe_wrapper_calls_wrapped_function_with_tracer(self, mock_traced):
        @safe_wrapper
        def my_handler(event, context):
            return "Hello, world!"

        mock_traced.side_effect = lambda x: x

        mock_lambda_context = LambdaContext(
            invoke_id="invoke_id",
            client_context={},
            cognito_identity={},
            epoch_deadline_time_in_ms=int(time.time() * 1000) + 10000,
        )

        assert my_handler({}, mock_lambda_context) == "Hello, world!"
        mock_traced.assert_called_once()

    @patch.dict(os.environ, {"SAFE_INIT_AUTO_TRACE_LAMBDAS": "false"})
    @patch("safe_init.tracer.traced")
    def test_safe_wrapper_calls_wrapped_function_with_no_tracer_if_disabled(self, mock_traced):
        @safe_wrapper
        def my_handler(event, context):
            return "Hello, world!"

        mock_traced.side_effect = lambda x: x

        mock_lambda_context = LambdaContext(
            invoke_id="invoke_id",
            client_context={},
            cognito_identity={},
            epoch_deadline_time_in_ms=int(time.time() * 1000) + 10000,
        )

        assert my_handler({}, mock_lambda_context) == "Hello, world!"
        mock_traced.assert_not_called()

    @patch.dict(os.environ, {"SAFE_INIT_AUTO_TRACE_LAMBDAS": "true"})
    @patch("safe_init.tracer.traced")
    def test_safe_wrapper_calls_wrapped_function_with_no_tracer_if_not_a_lambda(self, mock_traced):
        @safe_wrapper
        def my_fn():
            return "Hello, world!"

        mock_traced.side_effect = lambda x: x

        assert my_fn() == "Hello, world!"
        mock_traced.assert_not_called()
