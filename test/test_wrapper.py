from unittest.mock import patch

import pytest


class TestInitHandler:
    @patch("os.getenv", return_value="test.test_module.test_handler")
    @patch("test.test_module.test_handler")
    def test_init_handler_success(self, mock_handler, _):
        from safe_init.handler import _init_handler

        mock_handler.return_value = "success"
        handler = _init_handler()
        assert handler() == "success"

    @patch("os.getenv", return_value="")
    def test_init_handler_missing_env_var(self, _):
        from safe_init.handler import SafeInitError, _init_handler

        with pytest.raises(SafeInitError, match="SAFE_INIT_HANDLER environment variable is not set"):
            _init_handler()

    @patch("os.getenv", return_value="test.nonexistent_module.nonexistent_handler")
    @patch("safe_init.handler.slack_notify")
    @patch("safe_init.handler.sentry_capture", return_value=False)
    @patch("safe_init.handler.log_exception")
    def test_init_handler_import_error(self, mock_log_exception, mock_sentry_capture, mock_slack_notify, _):
        from safe_init.handler import _init_handler

        with pytest.raises(ModuleNotFoundError):
            _init_handler()
        mock_log_exception.assert_called_once_with("Failed to import handler", sentry_capture_result=False)
        mock_sentry_capture.assert_called_once()
        mock_slack_notify.assert_called_once()
        assert mock_slack_notify.call_args[0][0] == "Failed to import handler"

    @patch("os.getenv", return_value="test.test_module.test_handler")
    @patch("test.test_module.test_handler")
    @patch("safe_init.decorator.slack_notify")
    @patch("safe_init.decorator.log_exception")
    @patch("safe_init.decorator.sentry_capture", return_value=True)
    def test_init_handler_unexpected_runtime_error_with_sentry(
        self, mock_sentry_capture, mock_log_exception, mock_slack_notify, mock_handler, _
    ):
        from safe_init.handler import _init_handler

        mock_handler.side_effect = ValueError("unexpected error")
        with pytest.raises(Exception):
            _init_handler()()
        mock_log_exception.assert_called_once_with("Unhandled runtime exception detected", sentry_capture_result=True)
        mock_slack_notify.assert_not_called()
        mock_sentry_capture.assert_called_once_with(mock_handler.side_effect)

    @patch("os.getenv", return_value="test.test_module.test_handler")
    @patch("test.test_module.test_handler")
    @patch("safe_init.decorator.slack_notify")
    @patch("safe_init.decorator.log_exception")
    @patch("safe_init.decorator.sentry_capture", return_value=False)
    def test_init_handler_unexpected_runtime_error_with_sentry_failed(
        self, mock_sentry_capture, mock_log_exception, mock_slack_notify, mock_handler, _
    ):
        from safe_init.handler import _init_handler

        mock_handler.side_effect = ValueError("unexpected error")
        with pytest.raises(Exception):
            _init_handler()()
        mock_log_exception.assert_called_once_with("Unhandled runtime exception detected", sentry_capture_result=False)
        mock_slack_notify.assert_called_once()
        mock_sentry_capture.assert_called_once_with(mock_handler.side_effect)
