"""
This module provides a function for sending a Slack notification with error details.
"""

import os
from typing import cast

from safe_init.utils import is_lambda_context


def get_slack_webhook_url() -> str:
    """
    Returns the Slack webhook URL.

    Returns:
        The Slack webhook URL.
    """
    if "safe_init_slack_webhook_url" in globals():
        return cast(str, globals()["safe_init_slack_webhook_url"])
    slack_webhook_url = os.environ.get("SAFE_INIT_SLACK_WEBHOOK_URL")
    if not slack_webhook_url:
        msg = "SLACK_WEBHOOK_URL environment variable nor global variable are not set"
        raise ValueError(msg)
    return slack_webhook_url


def slack_notify(
    context_message: str,
    e: Exception,
    *,
    handler_name: str | None = None,
    lambda_context: object | None = None,
    sentry_capture_result: bool | None = None,
    message_title: str | None = None,
    additional_context: str | None = None,
) -> None:
    """
    Sends a Slack notification with error details.

    Args:
        context_message: A message describing the context of the error.
        e: The exception that was raised.
        handler_name: The name of the handler function that raised the exception.
        lambda_context: The Lambda context object, if running in a Lambda environment.
        sentry_capture_result: The result of attempting to capture the exception with Sentry.
        message_title: The title of the Slack message.
        additional_context: Additional context to include in the Slack message.

    Returns:
        None.
    """
    try:
        slack_webhook_url = get_slack_webhook_url()
    except ValueError:
        from safe_init.safe_logging import log_warning

        log_warning("Slack webhook URL is not set, skipping Slack notification")
        return

    import requests

    from safe_init.safe_logging import log_error, log_exception

    _lambda_context = None
    if lambda_context:
        if not is_lambda_context(lambda_context):
            log_error("lambda_context is not an instance of LambdaContext")
        else:
            from awslambdaric.lambda_context import LambdaContext

            _lambda_context = cast(LambdaContext, lambda_context)

    env = os.environ.get("SAFE_INIT_ENV", "unknown").upper()

    main_context = []

    if handler_name:
        main_context.append(
            {
                "type": "mrkdwn",
                "text": f":point_right: *Handler:* {handler_name}",
            },
        )
    if _lambda_context:
        main_context.extend(
            [
                {
                    "type": "mrkdwn",
                    "text": f":point_right: *AWS Request ID:* {_lambda_context.aws_request_id}",
                },
                {
                    "type": "mrkdwn",
                    "text": f":point_right: *Lambda function name:* {_lambda_context.function_name}",
                },
            ],
        )

    if dd_wrapped_handler := os.environ.get("DD_LAMBDA_HANDLER"):
        main_context.append(
            {
                "type": "mrkdwn",
                "text": f":point_right: *ddtrace-wrapped:* {dd_wrapped_handler}",
            },
        )

    if (lambda_name := os.environ.get("AWS_LAMBDA_FUNCTION_NAME")) and not _lambda_context:
        main_context.append(
            {
                "type": "mrkdwn",
                "text": f":point_right: *Lambda name:* {lambda_name}",
            },
        )

    if not message_title:
        message_title = f"{'Application' if not _lambda_context else 'Lambda'} execution failed"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"[{env}] {message_title} :hear_no_evil:",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "plain_text",
                    "text": context_message,
                },
            ],
        },
        {
            "type": "divider",
        },
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": f":face_palm: {e}",
            },
        },
        {
            "type": "context",
            "elements": main_context,
        },
    ]

    if additional_context:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": additional_context,
                },
            },
        )

    if sentry_capture_result is not None:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": (
                        ":rage: There also was an error sending the event to Sentry."
                        if not sentry_capture_result
                        else ":pepeok: The error has been sent to Sentry."
                    ),
                },
            },
        )

    slack_message = {
        "text": f"[{env}] Safe Init — {message_title} :pleading_face:",
        "attachments": [
            {"color": "#e12424", "blocks": blocks},
        ],
    }

    try:
        response = requests.post(slack_webhook_url, json=slack_message, timeout=15)

        if response.status_code != 200:  # noqa: PLR2004
            log_error(f"Failed to send Slack message: {response.text}", message=slack_message)
    except Exception:
        log_exception("Slack message sending exception", message=slack_message)
