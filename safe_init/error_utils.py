from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeAlias, TypeVar

from safe_init.safe_logging import log_error

_P = ParamSpec("_P")
_R = TypeVar("_R")

ExceptionsType: TypeAlias = type[BaseException] | tuple[type[BaseException], ...]


def suppress_exceptions(
    exceptions: ExceptionsType = Exception,
    *,
    default_return_value: _R | None = None,
    log_exception: bool = True,
) -> Callable[[Callable[_P, _R | Any]], Callable[_P, _R | None]]:
    """
    A decorator that suppresses specified exceptions raised by the wrapped function and returns a default value instead.

    Args:
        exceptions: An exception or a tuple of exceptions to suppress. Defaults to `Exception`.
        default_return_value: The default value to return if an exception is raised. Defaults to `None`.
        log_exception: Whether to log the suppressed exception. Defaults to `True`.

    Returns:
        A decorator that wraps the function, suppressing specified exceptions and returning a default value if an
        exception occurs.

    Example:
        @suppress_exceptions((ValueError, TypeError), default_return_value=0)
        def divide(a: int, b: int) -> float:
            return a / b
    """

    def decorator(func: Callable[_P, _R]) -> Callable[_P, _R | None]:
        @wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R | None:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if log_exception:
                    log_error(
                        f"Suppressed exception in {func.__name__}",
                        func_name=func.__name__,
                        func_args=args,
                        func_kwargs=kwargs,
                        default_return_value=default_return_value,
                        exc_info=e,
                    )
                return default_return_value

        return wrapper

    return decorator
