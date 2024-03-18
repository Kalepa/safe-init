"""
This module provides a decorator that traces the execution time of all function calls within the decorated function.
"""

import sys
import time
from collections.abc import Callable
from functools import wraps
from types import FrameType
from typing import Any, NamedTuple

CODE_PATH_BLACKLIST = ["/.pyenv/", "<frozen", "/var/lang/"]

_active_calls = {}
_function_calls = []
_traced = False


class FunctionCall(NamedTuple):
    """
    Represents a single function call that was traced by the `traced` decorator.

    Attributes:
    - function_name: The name of the function that was called.
    - execution_time: The time it took to execute the function, in seconds.
    - file_name: The name of the file where the function is defined.
    """

    function_name: str
    execution_time: float
    file_name: str


class FunctionCallSummary(NamedTuple):
    """
    Represents a single function call that was traced by the `traced` decorator.

    Attributes:
    - function_name: The name of the function that was called.
    - execution_count: The number of times the function was called.
    - total_execution_time: The total time it took to execute the function, in seconds.
    - file_name: The name of the file where the function is defined.
    """

    function_name: str
    execution_count: int
    total_execution_time: float
    file_name: str


def on_frame(frame: FrameType, event: str, arg: Any) -> None:  # noqa: ARG001, ANN401
    """
    A callback function that is called by the `sys.setprofile` function on every Python function call and return.
    It's used to trace the execution time of all function calls within the decorated function.

    It *is not safe* to use in environments with concurrent executions.

    Args:
    - frame: The current frame object.
    - event: The type of the event that triggered the callback. Can be either "call", "return", "c_call", or "c_return".
    - arg: The argument that was passed to the function that triggered the callback.
    """
    if any(blacklisted in frame.f_code.co_filename for blacklisted in CODE_PATH_BLACKLIST):
        return

    current_time = time.time()
    frame_id = id(frame)

    global _active_calls
    if event == "call":
        _active_calls[frame_id] = current_time
    elif event == "return" and frame_id in _active_calls:
        global _function_calls
        start_time = _active_calls.pop(frame_id)
        execution_time = current_time - start_time
        function_name = frame.f_code.co_qualname or frame.f_code.co_name
        _function_calls.append(FunctionCall(function_name, execution_time, frame.f_code.co_filename))


def is_traced() -> bool:
    """
    Returns whether the `traced` decorator was used to trace the execution time of function calls.
    """
    return _traced


def get_function_calls() -> list[FunctionCall]:
    """
    Returns a list of all function calls that were traced by the `traced` decorator.
    """
    return _function_calls


def traced(func: Callable) -> Callable:
    """
    Decorator that traces the execution time of all function calls within the decorated function.
    It's intended to be used only on Lambda handler functions and *is not safe* to use in environments with concurrent
    executions of the same function (e.g. FastAPI, Flask).

    Example usage:
    ```
    @bind_lambda_logging_context
    @traced
    def lambda_handler(event, context):
        # Your code here
    ```
    """
    global _traced
    _traced = False

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:  # type: ignore[no-untyped-def] # noqa: ANN002, ANN401
        global _function_calls, _active_calls, _traced
        _function_calls = []
        _active_calls = {}
        _traced = True

        sys.setprofile(on_frame)
        try:
            result = func(*args, **kwargs)
        finally:
            sys.setprofile(None)
        return result

    return wrapper
