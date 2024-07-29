from collections.abc import Callable
from contextvars import ContextVar
from unittest.mock import MagicMock, patch

from safe_init.safe_logging import log_error, log_exception, log_warning


class TestSafeLogging:
    @patch("safe_init.safe_logging.get_logger")
    def test_log_warning(self, mock_get_logger):
        log_warning("test warning")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().warning.assert_called_once_with("Safe Init: test warning")

    @patch("safe_init.safe_logging.get_logger")
    def test_log_warning_with_multiple_args(self, mock_get_logger):
        log_warning("test warning", "arg2", "arg3")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().warning.assert_called_once_with("Safe Init: test warning", "arg2", "arg3")

    @patch("safe_init.safe_logging.get_logger")
    def test_log_warning_with_kwargs(self, mock_get_logger):
        log_warning("test warning", arg1="value1", arg2="value2")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().warning.assert_called_once_with("Safe Init: test warning", arg1="value1", arg2="value2")

    @patch("safe_init.safe_logging.get_logger")
    def test_log_warning_with_empty_args(self, mock_get_logger):
        log_warning()
        mock_get_logger.assert_called_once_with()
        mock_get_logger().warning.assert_called_once_with()

    @patch("safe_init.safe_logging.get_logger")
    def test_log_warning_with_non_string_first_arg(self, mock_get_logger):
        log_warning(123, "arg2", "arg3")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().warning.assert_called_once_with(123, "arg2", "arg3")

    @patch("safe_init.safe_logging.get_logger")
    def test_log_warning_with_empty_string_first_arg(self, mock_get_logger):
        log_warning("", "arg2", "arg3")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().warning.assert_called_once_with("Safe Init: ", "arg2", "arg3")

    @patch("safe_init.safe_logging.get_logger")
    def test_log_error(self, mock_get_logger):
        log_error("test error")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().error.assert_called_once_with("Safe Init: test error")

    @patch("safe_init.safe_logging.get_logger")
    def test_log_error_with_multiple_args(self, mock_get_logger):
        log_error("test error", "arg2", "arg3")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().error.assert_called_once_with("Safe Init: test error", "arg2", "arg3")

    @patch("safe_init.safe_logging.get_logger")
    def test_log_error_with_kwargs(self, mock_get_logger):
        log_error("test error", arg1="value1", arg2="value2")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().error.assert_called_once_with("Safe Init: test error", arg1="value1", arg2="value2")

    @patch("safe_init.safe_logging.get_logger")
    def test_log_error_with_empty_args(self, mock_get_logger):
        log_error()
        mock_get_logger.assert_called_once_with()
        mock_get_logger().error.assert_called_once_with()

    @patch("safe_init.safe_logging.get_logger")
    def test_log_error_with_non_string_first_arg(self, mock_get_logger):
        log_error(123, "arg2", "arg3")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().error.assert_called_once_with(123, "arg2", "arg3")

    @patch("safe_init.safe_logging.get_logger")
    def test_log_error_with_empty_string_first_arg(self, mock_get_logger):
        log_error("", "arg2", "arg3")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().error.assert_called_once_with("Safe Init: ", "arg2", "arg3")

    @patch("safe_init.safe_logging.get_logger")
    def test_log_exception(self, mock_get_logger):
        log_exception("test exception")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().exception.assert_called_once_with("Safe Init: test exception")

    @patch("safe_init.safe_logging.get_logger")
    def test_log_exception_with_multiple_args(self, mock_get_logger):
        log_exception("test exception", "arg2", "arg3")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().exception.assert_called_once_with("Safe Init: test exception", "arg2", "arg3")

    @patch("safe_init.safe_logging.get_logger")
    def test_log_exception_with_kwargs(self, mock_get_logger):
        log_exception("test exception", arg1="value1", arg2="value2")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().exception.assert_called_once_with("Safe Init: test exception", arg1="value1", arg2="value2")

    @patch("safe_init.safe_logging.get_logger")
    def test_log_exception_with_empty_args(self, mock_get_logger):
        log_exception()
        mock_get_logger.assert_called_once_with()
        mock_get_logger().exception.assert_called_once_with()

    @patch("safe_init.safe_logging.get_logger")
    def test_log_exception_with_non_string_first_arg(self, mock_get_logger):
        log_exception(123, "arg2", "arg3")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().exception.assert_called_once_with(123, "arg2", "arg3")

    @patch("safe_init.safe_logging.get_logger")
    def test_log_exception_with_empty_string_first_arg(self, mock_get_logger):
        log_exception("", "arg2", "arg3")
        mock_get_logger.assert_called_once_with()
        mock_get_logger().exception.assert_called_once_with("Safe Init: ", "arg2", "arg3")

    @patch("safe_init.safe_logging._get_structlog_logger")
    def test_logger_uses_default_logger(self, mock_get_default_logger):
        mocked_logger = MagicMock()
        mock_get_default_logger.return_value = mocked_logger
        from safe_init.safe_logging import get_logger

        assert get_logger() == mocked_logger
        mock_get_default_logger.assert_called_once_with()

    @patch("safe_init.safe_logging._get_structlog_logger")
    def test_logger_can_be_overriden(self, mock_get_default_logger):
        mocked_logger = MagicMock()
        mocked_logger_getter = MagicMock(return_value=mocked_logger)
        safe_init_logger_getter: ContextVar[Callable] = ContextVar("safe_init_logger_getter")
        safe_init_logger_getter.set(mocked_logger_getter)
        from safe_init.safe_logging import get_logger

        assert get_logger() == mocked_logger
        mock_get_default_logger.assert_not_called()
        mocked_logger_getter.assert_called_once_with()
