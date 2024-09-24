from typing import Any
from unittest.mock import patch

import pytest

from safe_init.error_utils import suppress_exceptions


def test_no_exception():
    @suppress_exceptions()
    def func() -> int:
        return 10

    assert func() == 10


def test_suppress_exception():
    @suppress_exceptions(default_return_value="default")
    def func() -> str:
        raise Exception("An error occurred")

    assert func() == "default"


def test_default_return_value_none():
    @suppress_exceptions()
    def func() -> Any:
        raise Exception("An error occurred")

    assert func() is None


def test_suppress_specified_exception():
    @suppress_exceptions(exceptions=ValueError, default_return_value="value_error")
    def func() -> str:
        raise ValueError("A ValueError occurred")

    assert func() == "value_error"


def test_do_not_suppress_other_exceptions():
    @suppress_exceptions(exceptions=ValueError, default_return_value="value_error")
    def func() -> str:
        raise TypeError("A TypeError occurred")

    with pytest.raises(TypeError):
        func()


def test_suppress_multiple_exceptions():
    @suppress_exceptions(exceptions=(ValueError, TypeError), default_return_value="error")
    def func() -> str:
        raise TypeError("A TypeError occurred")

    assert func() == "error"


def test_function_signature_preserved():
    @suppress_exceptions()
    def func(a: int, b: int) -> int:
        return a + b

    assert func.__name__ == "func"
    assert func.__doc__ is None or func.__doc__ == ""


def test_return_type():
    @suppress_exceptions(default_return_value=0)
    def func() -> int:
        return 10

    result = func()
    assert isinstance(result, int)
    assert result == 10


def test_return_default_type():
    @suppress_exceptions(default_return_value=0)
    def func() -> int:
        raise Exception("An error occurred")

    result = func()
    assert isinstance(result, int)
    assert result == 0


def test_args_kwargs():
    @suppress_exceptions()
    def func(a: int, b: int = 5) -> int:
        return a + b

    assert func(3) == 8
    assert func(3, b=7) == 10


@patch("safe_init.error_utils.log_error")
def test_log_exception_true(mock_log_error):
    @suppress_exceptions(log_exception=True)
    def func() -> None:
        raise Exception("An error occurred")

    func()
    mock_log_error.assert_called_once()
    args, kwargs = mock_log_error.call_args
    assert "Suppressed exception in func" in args[0]


@patch("safe_init.error_utils.log_error")
def test_log_exception_false(mock_log_error):
    @suppress_exceptions(log_exception=False)
    def func() -> None:
        raise Exception("An error occurred")

    func()
    mock_log_error.assert_not_called()


@patch("safe_init.error_utils.log_error")
def test_exception_message_in_log(mock_log_error):
    @suppress_exceptions(log_exception=True)
    def func() -> None:
        raise Exception("An error occurred")

    func()
    mock_log_error.assert_called_once()
    args, kwargs = mock_log_error.call_args
    assert "Suppressed exception in func" in args[0]
    assert "exc_info" in kwargs
    assert isinstance(kwargs["exc_info"], Exception)
    assert str(kwargs["exc_info"]) == "An error occurred"


def test_multiple_calls():
    counter = 0

    @suppress_exceptions(default_return_value=-1)
    def func() -> int:
        nonlocal counter
        counter += 1
        if counter % 2 == 0:
            raise Exception("Even call")
        return counter

    results = [func() for _ in range(5)]
    assert results == [1, -1, 3, -1, 5]


def test_exception_not_suppressed():
    @suppress_exceptions(exceptions=(), default_return_value="default")
    def func() -> None:
        raise Exception("An error occurred")

    with pytest.raises(Exception):
        assert func() == "default"


def test_decorator_without_arguments():
    @suppress_exceptions()
    def func() -> None:
        raise Exception("An error occurred")

    assert func() is None
