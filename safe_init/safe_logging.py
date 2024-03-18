"""
This module provides functions for logging messages with a "Safe Init" prefix.
"""

import os
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger


def _get_structlog_logger() -> "BoundLogger":
    """
    Initializes and returns a StructLog logger instance with the appropriate processors based on the environment.

    Returns:
        The structlog logger instance.
    """
    import structlog

    if not structlog.is_configured():
        import logging  # allow-stdlib-logging

        from structlog.processors import CallsiteParameter

        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.CallsiteParameterAdder(
                [CallsiteParameter.FILENAME, CallsiteParameter.FUNC_NAME, CallsiteParameter.LINENO],
            ),
            structlog.processors.TimeStamper(fmt="iso"),
        ]

        if sys.stderr.isatty() or os.environ.get("SAFE_INIT_LOGGING_USE_CONSOLE_RENDERER", "False").lower() == "true":
            # List of processors to use when logging to a terminal
            processors.extend(
                [
                    structlog.processors.format_exc_info,
                    structlog.dev.ConsoleRenderer(),
                ],
            )
        else:
            # List of processors to use when the app is running in its runtime environment
            processors.extend(
                [
                    structlog.processors.dict_tracebacks,
                    structlog.processors.EventRenamer("message", "_event"),
                    structlog.processors.JSONRenderer(),
                ],
            )

        structlog.configure(
            cache_logger_on_first_use=True,
            wrapper_class=structlog.make_filtering_bound_logger(
                logging.INFO if not os.getenv("SAFE_INIT_DEBUG") else logging.DEBUG,
            ),
            processors=processors,  # type: ignore[arg-type]
        )

    return structlog.get_logger()


def get_logger() -> "BoundLogger":
    """
    Get the logger instance to use throughout the code.

    Returns:
        The logger instance.
    """
    if globals().get("safe_init_logger_getter"):
        return globals()["safe_init_logger_getter"]()
    return _get_structlog_logger()


def _add_prefix(args: tuple[Any, ...]) -> tuple[Any, ...]:
    """
    Adds "Safe Init" prefix to the first argument of the given tuple, if it is a string.
    Returns the modified tuple.
    """
    if not isinstance(args, str) and len(args) > 0 and isinstance(args[0], str):
        args_list = list(args)
        args_list[0] = f"Safe Init: {args[0]}"
        return tuple(args_list)
    return args


def log_debug(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401
    """
    Logs a debug message with the "Safe Init" prefix.
    """
    if not os.getenv("SAFE_INIT_DEBUG"):
        return
    get_logger().info(*_add_prefix(args), **kwargs)


def log_info(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401
    """
    Logs a info message with the "Safe Init" prefix.
    """
    get_logger().info(*_add_prefix(args), **kwargs)


def log_warning(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401
    """
    Logs a warning message with the "Safe Init" prefix.
    """
    get_logger().warning(*_add_prefix(args), **kwargs)


def log_error(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401
    """
    Logs an error message with the "Safe Init" prefix.
    """
    get_logger().error(*_add_prefix(args), **kwargs)


def log_exception(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401
    """
    Logs an error message with the "Safe Init" prefix and exception traceback.
    """
    get_logger().exception(*_add_prefix(args), **kwargs)
