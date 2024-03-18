import os
from unittest.mock import patch

import requests

from safe_init.slack import slack_notify


@patch.dict(os.environ, {"SAFE_INIT_SLACK_WEBHOOK_URL": "test_url"})
class TestSlackNotify:
    @patch("requests.post")
    @patch.dict(os.environ, {"SAFE_INIT_ENV": "test", "AWS_LAMBDA_FUNCTION_NAME": "lol"})
    def test_slack_notify_success(self, mock_post):
        context_message = "Test context message"
        e = Exception("Test exception")
        handler_name = "Test handler name"
        lambda_context = None
        sentry_capture_result = True

        slack_notify(
            context_message,
            e,
            handler_name=handler_name,
            lambda_context=lambda_context,
            sentry_capture_result=sentry_capture_result,
        )

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["text"] == "[TEST] Safe Init — Application execution failed :pleading_face:"
        assert kwargs["json"]["attachments"][0]["color"] == "#e12424"
        assert (
            kwargs["json"]["attachments"][0]["blocks"][0]["text"]["text"]
            == "[TEST] Application execution failed :hear_no_evil:"
        )
        assert kwargs["json"]["attachments"][0]["blocks"][1]["elements"][0]["text"] == context_message
        assert kwargs["json"]["attachments"][0]["blocks"][3]["text"]["text"] == f":face_palm: {e}"
        assert (
            kwargs["json"]["attachments"][0]["blocks"][4]["elements"][0]["text"]
            == f":point_right: *Handler:* {handler_name}"
        )
        assert (
            kwargs["json"]["attachments"][0]["blocks"][4]["elements"][1]["text"] == ":point_right: *Lambda name:* lol"
        )
        assert (
            kwargs["json"]["attachments"][0]["blocks"][5]["text"]["text"]
            == ":pepeok: The error has been sent to Sentry."
        )

    @patch("requests.post", side_effect=requests.exceptions.Timeout)
    @patch("safe_init.safe_logging.log_exception")
    @patch.dict(os.environ, {"SAFE_INIT_ENV": "test", "AWS_LAMBDA_FUNCTION_NAME": "lol"})
    def test_slack_notify_timeout(self, mock_log_exception, mock_post):
        context_message = "Test context message"
        e = Exception("Test exception")
        handler_name = "Test handler name"
        lambda_context = None
        sentry_capture_result = False

        slack_notify(
            context_message,
            e,
            handler_name=handler_name,
            lambda_context=lambda_context,
            sentry_capture_result=sentry_capture_result,
        )

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["text"] == "[TEST] Safe Init — Application execution failed :pleading_face:"
        assert kwargs["json"]["attachments"][0]["color"] == "#e12424"
        assert (
            kwargs["json"]["attachments"][0]["blocks"][0]["text"]["text"]
            == "[TEST] Application execution failed :hear_no_evil:"
        )
        assert kwargs["json"]["attachments"][0]["blocks"][1]["elements"][0]["text"] == context_message
        assert kwargs["json"]["attachments"][0]["blocks"][3]["text"]["text"] == f":face_palm: {e}"
        assert (
            kwargs["json"]["attachments"][0]["blocks"][4]["elements"][0]["text"]
            == f":point_right: *Handler:* {handler_name}"
        )
        assert (
            kwargs["json"]["attachments"][0]["blocks"][4]["elements"][1]["text"] == ":point_right: *Lambda name:* lol"
        )
        assert (
            kwargs["json"]["attachments"][0]["blocks"][5]["text"]["text"]
            == ":rage: There also was an error sending the event to Sentry."
        )
        mock_log_exception.assert_called_once()
        args, kwargs = mock_log_exception.call_args
        assert args[0] == "Slack message sending exception"

    @patch("requests.post", side_effect=requests.exceptions.RequestException)
    @patch("safe_init.safe_logging.log_exception")
    @patch.dict(os.environ, {"SAFE_INIT_ENV": "test"})
    def test_slack_notify_request_exception(self, mock_log_exception, mock_post):
        context_message = "Test context message"
        e = Exception("Test exception")
        handler_name = "Test handler name"
        lambda_context = None
        sentry_capture_result = True

        slack_notify(
            context_message,
            e,
            handler_name=handler_name,
            lambda_context=lambda_context,
            sentry_capture_result=sentry_capture_result,
        )

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["text"] == "[TEST] Safe Init — Application execution failed :pleading_face:"
        assert kwargs["json"]["attachments"][0]["color"] == "#e12424"
        assert (
            kwargs["json"]["attachments"][0]["blocks"][0]["text"]["text"]
            == "[TEST] Application execution failed :hear_no_evil:"
        )
        assert kwargs["json"]["attachments"][0]["blocks"][1]["elements"][0]["text"] == context_message
        assert kwargs["json"]["attachments"][0]["blocks"][3]["text"]["text"] == f":face_palm: {e}"
        assert (
            kwargs["json"]["attachments"][0]["blocks"][4]["elements"][0]["text"]
            == f":point_right: *Handler:* {handler_name}"
        )
        assert (
            kwargs["json"]["attachments"][0]["blocks"][5]["text"]["text"]
            == ":pepeok: The error has been sent to Sentry."
        )
        mock_log_exception.assert_called_once()
        args, kwargs = mock_log_exception.call_args
        assert args[0] == "Slack message sending exception"

    @patch.dict(os.environ, {"SAFE_INIT_ENV": "test"})
    def test_slack_notify_lambda_context(self):
        context_message = "Test context message"
        e = Exception("Test exception")
        handler_name = "Test handler name"
        lambda_context = type(
            "LambdaContext", (), {"aws_request_id": "Test request id", "function_name": "Test function name"}
        )()
        sentry_capture_result = True

        with patch("requests.post") as mock_post:
            slack_notify(
                context_message,
                e,
                handler_name=handler_name,
                lambda_context=lambda_context,
                sentry_capture_result=sentry_capture_result,
            )

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["text"] == "[TEST] Safe Init — Lambda execution failed :pleading_face:"
        assert kwargs["json"]["attachments"][0]["color"] == "#e12424"
        assert (
            kwargs["json"]["attachments"][0]["blocks"][0]["text"]["text"]
            == "[TEST] Lambda execution failed :hear_no_evil:"
        )
        assert kwargs["json"]["attachments"][0]["blocks"][1]["elements"][0]["text"] == context_message
        assert kwargs["json"]["attachments"][0]["blocks"][3]["text"]["text"] == f":face_palm: {e}"
        assert (
            kwargs["json"]["attachments"][0]["blocks"][4]["elements"][0]["text"]
            == f":point_right: *Handler:* {handler_name}"
        )
        assert (
            kwargs["json"]["attachments"][0]["blocks"][4]["elements"][1]["text"]
            == f":point_right: *AWS Request ID:* {lambda_context.aws_request_id}"
        )
        assert (
            kwargs["json"]["attachments"][0]["blocks"][4]["elements"][2]["text"]
            == f":point_right: *Lambda function name:* {lambda_context.function_name}"
        )

    @patch.dict(os.environ, {"SAFE_INIT_ENV": "test"})
    def test_slack_notify_dd_wrapped_handler(self):
        context_message = "Test context message"
        e = Exception("Test exception")
        handler_name = "Test handler name"
        lambda_context = None
        sentry_capture_result = True
        os.environ["DD_LAMBDA_HANDLER"] = "Test dd handler"

        with patch("requests.post") as mock_post:
            slack_notify(
                context_message,
                e,
                handler_name=handler_name,
                lambda_context=lambda_context,
                sentry_capture_result=sentry_capture_result,
            )

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["text"] == "[TEST] Safe Init — Application execution failed :pleading_face:"
        assert kwargs["json"]["attachments"][0]["color"] == "#e12424"
        assert (
            kwargs["json"]["attachments"][0]["blocks"][0]["text"]["text"]
            == "[TEST] Application execution failed :hear_no_evil:"
        )
        assert kwargs["json"]["attachments"][0]["blocks"][1]["elements"][0]["text"] == context_message
        assert kwargs["json"]["attachments"][0]["blocks"][3]["text"]["text"] == f":face_palm: {e}"
        assert (
            kwargs["json"]["attachments"][0]["blocks"][4]["elements"][0]["text"]
            == f":point_right: *Handler:* {handler_name}"
        )
        assert (
            kwargs["json"]["attachments"][0]["blocks"][4]["elements"][1]["text"]
            == f":point_right: *ddtrace-wrapped:* {os.environ['DD_LAMBDA_HANDLER']}"
        )

    @patch.dict(os.environ, {"SAFE_INIT_ENV": "test"})
    def test_slack_notify_lambda_name(self):
        context_message = "Test context message"
        e = Exception("Test exception")
        handler_name = "Test handler name"
        lambda_context = None
        sentry_capture_result = True
        os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "Test lambda name"

        with patch("requests.post") as mock_post:
            slack_notify(
                context_message,
                e,
                handler_name=handler_name,
                lambda_context=lambda_context,
                sentry_capture_result=sentry_capture_result,
            )

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["text"] == "[TEST] Safe Init — Application execution failed :pleading_face:"
        assert kwargs["json"]["attachments"][0]["color"] == "#e12424"
        assert (
            kwargs["json"]["attachments"][0]["blocks"][0]["text"]["text"]
            == "[TEST] Application execution failed :hear_no_evil:"
        )
        assert kwargs["json"]["attachments"][0]["blocks"][1]["elements"][0]["text"] == context_message
        assert kwargs["json"]["attachments"][0]["blocks"][3]["text"]["text"] == f":face_palm: {e}"
        assert (
            kwargs["json"]["attachments"][0]["blocks"][4]["elements"][0]["text"]
            == f":point_right: *Handler:* {handler_name}"
        )
        assert len(kwargs["json"]["attachments"][0]["blocks"]) == 6
