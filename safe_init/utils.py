import contextlib
import os
from collections.abc import Iterator, Mapping
from contextvars import Context, copy_context
from typing import Any

from safe_init.tracer import FunctionCall, FunctionCallSummary

_sentry_sdk = None


def is_lambda_handler(args: Any) -> bool:  # noqa: ANN401
    """
    Returns True if the wrapped function is a Lambda handler.
    """
    return (
        len(args) == 2  # noqa: PLR2004
        and isinstance(args[1], object)
        and hasattr(type(args[1]), "__name__")
        and type(args[1]).__name__ == "LambdaContext"
        and hasattr(args[1], "function_name")
    )


def is_lambda_context(lambda_context: Any) -> bool:  # noqa: ANN401
    """
    Checks if the input object is an instance of LambdaContext.
    """

    # This is a naive check to ensure that the lambda_context is an instance of LambdaContext. We can't use
    # isinstance() because the LambdaContext class is not available in the runtime environment, and it's not the
    # class we import from external awslambdaric. We can, however, cast it to the LambdaContext type.
    if (
        not hasattr(type(lambda_context), "__name__")
        or type(lambda_context).__name__ != "LambdaContext"
        or not hasattr(lambda_context, "function_name")
    ):
        return False
    return True


def get_sentry_sdk() -> "sentry_sdk":  # type: ignore[name-defined] # noqa: F821
    """
    Returns the cached Sentry SDK object.

    Returns:
        The Sentry SDK object.
    """
    global _sentry_sdk
    if _sentry_sdk is None:
        import sentry_sdk

        _sentry_sdk = sentry_sdk
    return _sentry_sdk


def aggregate_traced_fn_calls(fn_calls: list[FunctionCall]) -> list[FunctionCallSummary]:
    """
    Aggregates the execution times of all function calls with the same name.

    Args:
        fn_calls: A list of function calls.

    Returns:
        A list of function call summaries.
    """
    calls_dict = {}
    for call in fn_calls:
        if call.function_name not in calls_dict:
            calls_dict[call.function_name] = (0, 0.0, call.file_name)
        calls_dict[call.function_name] = (
            calls_dict[call.function_name][0] + 1,
            calls_dict[call.function_name][1] + call.execution_time,
            call.file_name,
        )
    return [FunctionCallSummary(k, *v) for k, v in calls_dict.items()]


def format_traces(traces: list[FunctionCallSummary], limit: int) -> str:
    """
    Formats the function call traces as a Markdown string.

    Args:
        traces: A list of function call traces.
        limit: The maximum number of traces to include in the output.

    Returns:
        A Markdown string with the formatted traces.
    """
    home_paths = os.getenv("SAFE_INIT_TRACER_HOME_PATHS", "").split(",")
    home_mark = lambda path: ":zap:" if any(home in path for home in home_paths) else ""  # noqa: E731
    if not traces:
        return "_No function calls were traced_"
    return f"🕵️ *Top {limit} most time-consuming function call{'s' if limit != 1 else ''}:*\n" + "\n".join(
        f"{idx + 1}. `{fnc.function_name}`: *{fnc.total_execution_time:.3f}s*, called"
        f" {fnc.execution_count} time{'s' if fnc.execution_count != 1 else ''} (`{fnc.file_name}`)"
        f" {home_mark(fnc.file_name)}"
        for idx, fnc in enumerate(traces[:limit])
    )


@contextlib.contextmanager
def env(new_vars: Mapping[str, str | None]) -> Iterator:
    environ = os.environ
    to_update = {k: v for k, v in new_vars.items() if v is not None}
    to_remove = [k for k, v in new_vars.items() if v is None]

    stomped = (set(to_update.keys()) | set(to_remove)) & set(environ.keys())
    update_after = {k: environ[k] for k in stomped}
    remove_after = frozenset(k for k in to_update if k not in environ)

    try:
        for k, v in to_update.items():
            os.environ[k] = v
        [os.environ.pop(k, None) for k in to_remove]
        yield
    finally:
        for k, v in update_after.items():
            os.environ[k] = v
        [os.environ.pop(k, None) for k in remove_after]


def bool_env(var: str) -> bool:
    """
    Returns the boolean value of the environment variable.

    Args:
        var: The name of the environment variable.

    Returns:
        The boolean value of the environment variable.
    """
    return os.getenv(var, "").strip().lower() in ("1", "true", "yes", "on", "y")


def get_contextvar_named(name: str) -> Any | None:  # noqa: ANN401
    """
    Returns the context variable with the given name, or None if it does not exist.

    Args:
        name: The name of the context variable.

    Returns:
        The context variable.
    """
    ctx: Context = copy_context()
    try:
        cvar, cval = next(c for c in ctx.items() if c[0].name == name)
        return cval  # noqa: TRY300
    except:  # noqa: E722
        return None
