import json
import os
import time
from unittest.mock import MagicMock, patch

import botocore
import pytest
from awslambdaric.lambda_context import LambdaContext
from botocore.exceptions import ClientError

from safe_init.dlq import (
    SafeInitDummyHandler,
    _get_dlq_url,
    _get_sqs_client,
    _prepare_sqs_message,
    context_has_dlq,
    push_event_to_dlq,
)


class TestDLQ:
    @patch.dict(os.environ, {"SAFE_INIT_DLQ": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"})
    def test_context_has_dlq(self):
        assert context_has_dlq() is True

    @patch.dict(os.environ, {})
    def test_context_has_no_dlq(self):
        assert context_has_dlq() is False

    @patch.dict(os.environ, {"SAFE_INIT_DLQ": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"})
    @patch("safe_init.dlq._get_sqs_client")
    def test_push_event_to_dlq_lambda_handler(self, mock_get_sqs_client):
        mock_sqs_client = MagicMock()
        mock_get_sqs_client.return_value = mock_sqs_client
        mock_sqs_client.send_message.return_value = {"MessageId": "12345"}

        event = {"key": "value"}
        context = LambdaContext("id", None, None, 10000)
        context.function_name = "test-function"
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        args = (event, context)

        push_event_to_dlq(*args)

        mock_get_sqs_client.assert_called_once()
        mock_sqs_client.send_message.assert_called_once_with(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
            MessageBody=json.dumps(
                {
                    "type": "lambda",
                    "timestamp": int(time.time()),
                    "event": event,
                    "lambda_name": context.function_name,
                    "lambda_arn": context.invoked_function_arn,
                    "aws_request_id": context.aws_request_id,
                    "handler": "",
                }
            ),
        )

    @patch.dict(os.environ, {"SAFE_INIT_DLQ": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"})
    @patch("safe_init.dlq._get_sqs_client")
    def test_push_event_to_dlq_other_handler(self, mock_get_sqs_client):
        mock_sqs_client = MagicMock()
        mock_get_sqs_client.return_value = mock_sqs_client
        mock_sqs_client.send_message.return_value = {"MessageId": "12345"}

        args = ("arg1", "arg2")
        kwargs = {"key1": "value1", "key2": "value2"}

        push_event_to_dlq(*args, **kwargs)

        mock_get_sqs_client.assert_called_once()
        mock_sqs_client.send_message.assert_called_once_with(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
            MessageBody=json.dumps(
                {
                    "type": "other",
                    "timestamp": int(time.time()),
                    "args": args,
                    "kwargs": kwargs,
                    "handler": "",
                }
            ),
        )

    @patch.dict(os.environ, {"SAFE_INIT_DLQ": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"})
    @patch("safe_init.dlq._get_sqs_client")
    def test_push_event_to_dlq_error(self, mock_get_sqs_client):
        mock_sqs_client = MagicMock()
        mock_get_sqs_client.return_value = mock_sqs_client
        mock_sqs_client.send_message.side_effect = ClientError(
            error_response={"Error": {"Code": "TestException", "Message": "Test exception"}},
            operation_name="send_message",
        )

        args = ("arg1", "arg2")
        kwargs = {"key1": "value1", "key2": "value2"}

        timestamp = int(time.time())
        push_event_to_dlq(*args, **kwargs)

        mock_get_sqs_client.assert_called_once()
        mock_sqs_client.send_message.assert_called_once_with(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
            MessageBody=json.dumps(
                {
                    "type": "other",
                    "timestamp": timestamp,
                    "args": args,
                    "kwargs": kwargs,
                    "handler": "",
                }
            ),
        )

    @patch.dict(os.environ, {"SAFE_INIT_DLQ": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"})
    @patch("safe_init.dlq._get_sqs_client")
    def test_push_event_to_dlq_lambda_handler_with_handler_name(self, mock_get_sqs_client):
        mock_sqs_client = MagicMock()
        mock_get_sqs_client.return_value = mock_sqs_client
        mock_sqs_client.send_message.return_value = {"MessageId": "12345"}

        event = {"key": "value"}
        context = LambdaContext("id", None, None, 10000)
        context.function_name = "test-function"
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        args = (event, context)

        timestamp = int(time.time())
        with patch.dict(os.environ, {"SAFE_INIT_HANDLER": "test-handler"}):
            push_event_to_dlq(*args)

        mock_get_sqs_client.assert_called_once()
        mock_sqs_client.send_message.assert_called_once_with(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
            MessageBody=json.dumps(
                {
                    "type": "lambda",
                    "timestamp": timestamp,
                    "event": event,
                    "lambda_name": context.function_name,
                    "lambda_arn": context.invoked_function_arn,
                    "aws_request_id": context.aws_request_id,
                    "handler": "test-handler",
                }
            ),
        )

    @patch.dict(os.environ, {"SAFE_INIT_DLQ": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"})
    @patch("safe_init.dlq._get_sqs_client")
    def test_push_event_to_dlq_lambda_handler_with_invalid_context(self, mock_get_sqs_client):
        mock_sqs_client = MagicMock()
        mock_get_sqs_client.return_value = mock_sqs_client
        mock_sqs_client.send_message.return_value = {"MessageId": "12345"}

        event = {"key": "value"}
        context = "invalid-context"
        args = (event, context)

        timestamp = int(time.time())
        push_event_to_dlq(*args)

        mock_get_sqs_client.assert_called_once()
        mock_sqs_client.send_message.assert_called_once_with(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
            MessageBody=json.dumps(
                {
                    "type": "other",
                    "timestamp": timestamp,
                    "args": [{"key": "value"}, "invalid-context"],
                    "kwargs": {},
                    "handler": "",
                }
            ),
        )

    @patch.dict(os.environ, {"SAFE_INIT_DLQ": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"})
    @patch("safe_init.dlq.log_error")
    @patch("safe_init.dlq._get_sqs_client")
    def test_push_event_to_dlq_lambda_handler_with_invalid_exception(self, mock_get_sqs_client, mock_log_error):
        mock_sqs_client = MagicMock()
        mock_get_sqs_client.return_value = mock_sqs_client
        mock_sqs_client.send_message.return_value = {"MessageId": "12345"}

        event = {"key": "value"}
        context = LambdaContext("id", None, None, 10000)
        context.function_name = "test-function"
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        args = (event, context)

        with pytest.raises(Exception, match="Dummy handler initialized with an invalid exception: invalid-exception"):
            SafeInitDummyHandler("invalid-exception")(*args)

        mock_log_error.assert_called_once_with(
            "Dummy handler initialized with an invalid exception. Will use a custom one instead",
            passed_exc="invalid-exception",
        )

    @patch.dict(os.environ, {"SAFE_INIT_DLQ": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"})
    @patch("safe_init.dlq.context_has_dlq")
    @patch("safe_init.dlq.log_error")
    @patch("safe_init.dlq._get_sqs_client")
    def test_push_event_to_dlq_lambda_handler_with_no_dlq(
        self, mock_get_sqs_client, mock_log_error, mock_context_has_dlq
    ):
        mock_sqs_client = MagicMock()
        mock_get_sqs_client.return_value = mock_sqs_client
        mock_sqs_client.send_message.return_value = {"MessageId": "12345"}

        event = {"key": "value"}
        context = LambdaContext("id", None, None, 10000)
        context.function_name = "test-function"
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        args = (event, context)

        mock_context_has_dlq.return_value = False

        with pytest.raises(Exception, match="test-exception"):
            SafeInitDummyHandler(Exception("test-exception"))(*args)

        mock_log_error.assert_called_once_with(
            (
                "Dummy handler called without a DLQ configured. This should never happen and is a bug in the safe"
                " init code. Please report this to the infrastructure team"
            ),
            args=args,
            kwargs={},
        )
        mock_get_sqs_client.assert_not_called()
        mock_sqs_client.send_message.assert_not_called()

    @patch.dict(os.environ, {"SAFE_INIT_DLQ": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"})
    @patch("safe_init.dlq.context_has_dlq")
    @patch("safe_init.dlq.log_warning")
    @patch("safe_init.dlq._get_sqs_client")
    def test_push_event_to_dlq_lambda_handler_with_dlq(
        self, mock_get_sqs_client, mock_log_warning, mock_context_has_dlq
    ):
        mock_sqs_client = MagicMock()
        mock_get_sqs_client.return_value = mock_sqs_client
        mock_sqs_client.send_message.return_value = {"MessageId": "12345"}

        event = {"key": "value"}
        context = LambdaContext("id", None, None, 10000)
        context.function_name = "test-function"
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        args = (event, context)

        mock_context_has_dlq.return_value = True

        timestamp = int(time.time())
        with pytest.raises(Exception, match="test-exception"):
            SafeInitDummyHandler(Exception("test-exception"))(*args)

        mock_log_warning.assert_called_once_with(
            (
                "Application failed during the import phase. Using a dummy handler to fetch the event and send to a "
                "DLQ. The original exception will be re-raised"
            ),
            args=args,
            kwargs={},
        )
        mock_get_sqs_client.assert_called_once()
        mock_sqs_client.send_message.assert_called_once_with(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
            MessageBody=json.dumps(
                {
                    "type": "lambda",
                    "timestamp": timestamp,
                    "event": event,
                    "lambda_name": context.function_name,
                    "lambda_arn": context.invoked_function_arn,
                    "aws_request_id": context.aws_request_id,
                    "handler": "",
                }
            ),
        )

    @patch.dict(os.environ, {"SAFE_INIT_DLQ": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"})
    def test_get_dlq_url(self):
        assert _get_dlq_url() == "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"

    @patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-east-1"})
    def test_get_sqs_client(self):
        sqs_client = _get_sqs_client()
        assert isinstance(sqs_client, botocore.client.BaseClient)

    def test_prepare_sqs_message_lambda_handler(self):
        event = {"key": "value"}
        context = LambdaContext("id", None, None, 10000)
        context.function_name = "test-function"
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        args = (event, context)

        with patch.dict(os.environ, {"SAFE_INIT_HANDLER": "test-handler"}):
            message = _prepare_sqs_message(*args)

        assert message == {
            "MessageBody": json.dumps(
                {
                    "type": "lambda",
                    "timestamp": int(time.time()),
                    "event": event,
                    "lambda_name": context.function_name,
                    "lambda_arn": context.invoked_function_arn,
                    "aws_request_id": context.aws_request_id,
                    "handler": "test-handler",
                }
            )
        }

    def test_prepare_sqs_message_other_handler(self):
        args = ("arg1", "arg2")
        kwargs = {"key1": "value1", "key2": "value2"}

        message = _prepare_sqs_message(*args, **kwargs)

        assert message == {
            "MessageBody": json.dumps(
                {
                    "type": "other",
                    "timestamp": int(time.time()),
                    "args": args,
                    "kwargs": kwargs,
                    "handler": "",
                }
            )
        }
