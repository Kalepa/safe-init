import json
import os
import time
from typing import Any, cast

from boto3_type_annotations.sqs import Client as SQSClient

from safe_init.safe_logging import log_error, log_exception, log_warning
from safe_init.utils import is_lambda_context, is_lambda_handler

_sqs_client: SQSClient | None = None


def context_has_dlq() -> bool:
    """
    Returns True if the current execution context has a dead-letter queue configured.
    """
    return os.environ.get("SAFE_INIT_DLQ") is not None


def push_event_to_dlq(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401
    """
    Pushes the given event to the dead-letter queue configured for the current execution context.
    """
    try:
        dlq_url = _get_dlq_url()
        sqs_client = _get_sqs_client()
        sqs_client.send_message(QueueUrl=dlq_url, **_prepare_sqs_message(*args, **kwargs))
    except Exception:
        log_exception("There was an error pushing the event to the DLQ", args=args, kwargs=kwargs)


def preload_sqs_client() -> None:
    """
    Preloads the SQS client to avoid the first invocation penalty.
    """
    _get_sqs_client()


def _get_dlq_url() -> str:
    """
    Returns the URL of the dead-letter queue configured for the current execution context.
    """
    return os.environ["SAFE_INIT_DLQ"]


def _get_sqs_client() -> SQSClient:
    """
    Returns a boto3 SQS client.
    """
    global _sqs_client

    if _sqs_client is None:
        import boto3

        _sqs_client = boto3.client("sqs")

    return _sqs_client


def _prepare_sqs_message(*args: Any, **kwargs: Any) -> dict[str, Any]:  # noqa: ANN401
    """
    Prepares the given event to be sent to the dead-letter queue.
    """
    handler_name = os.getenv("SAFE_INIT_HANDLER", "").strip()
    if is_lambda_handler(args):
        if not is_lambda_context(args[1]):
            log_error("Second handler argument is not an instance of LambdaContext")
        else:
            from awslambdaric.lambda_context import LambdaContext

            lambda_context = cast(LambdaContext, args[1])

        dlq_event = {
            "type": "lambda",
            "timestamp": int(time.time()),
            "event": args[0],
            "lambda_name": lambda_context.function_name,
            "lambda_arn": lambda_context.invoked_function_arn,
            "aws_request_id": lambda_context.aws_request_id,
            "handler": handler_name,
        }
    else:
        dlq_event = {
            "type": "other",
            "timestamp": int(time.time()),
            "args": args,
            "kwargs": kwargs,
            "handler": handler_name,
        }

    return {"MessageBody": json.dumps(dlq_event)}


class SafeInitDummyHandler:
    """
    A dummy handler that's returned when the execution context has a DLQ configured and the safe init
    handler fails during the init phase. This handler is then returned to extract the input arguments
    and send them to the DLQ, then re-raise the original exception.
    """

    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        if not isinstance(exc, Exception):
            log_error(
                "Dummy handler initialized with an invalid exception. Will use a custom one instead",
                passed_exc=exc,
            )
            self._exc = Exception(f"Dummy handler initialized with an invalid exception: {exc}")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        if not context_has_dlq():
            log_error(
                (
                    "Dummy handler called without a DLQ configured. This should never happen and is a bug in the safe"
                    " init code. Please report this to the infrastructure team"
                ),
                args=args,
                kwargs=kwargs,
            )
            self._raise()

        log_warning(
            (
                "Application failed during the import phase. Using a dummy handler to fetch the event and send to a "
                "DLQ. The original exception will be re-raised"
            ),
            args=args,
            kwargs=kwargs,
        )
        push_event_to_dlq(*args, **kwargs)
        self._raise()

    def _raise(self) -> None:
        raise self._exc
