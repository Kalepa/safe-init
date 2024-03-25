from typing import Any

__VERSION__ = "0.1.0"

_wrapped_handler = None


class LazyHandler:
    @staticmethod
    def _init_handler() -> None:
        global _wrapped_handler
        if _wrapped_handler is None:
            from safe_init.handler import _init_handler

            _wrapped_handler = _init_handler()

    def __get__(self, instance, owner):
        self._init_handler()
        return _wrapped_handler

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self._init_handler()
        return _wrapped_handler(*args, **kwargs)


# Deprecation warning: LazyHandler is deprecated and will be removed in the near future.
# Use `safe_init.handler.handler` instead.
handler = LazyHandler()

__all__ = ["handler"]
