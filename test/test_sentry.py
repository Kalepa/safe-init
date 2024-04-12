import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def unload_module():
    to_unload = {mod for mod in sys.modules if mod.startswith("safe_init") or mod.startswith("sentry_sdk")}
    for mod in to_unload:
        del sys.modules[mod]

    yield


@patch.dict(os.environ, {"SENTRY_DSN": "test_dsn", "UNIT_TEST_SENTRY": "1"})
@patch("safe_init.sentry.log_warning")
@patch("sentry_sdk.init")
@patch("sentry_sdk.capture_exception")
def test_sentry_capture_with_sentry_installed(mock_capture, mock_init, mock_log_warning):
    from safe_init.sentry import sentry_capture

    exc = Exception("test exception")
    assert sentry_capture(exc) is True
    mock_log_warning.assert_not_called()
    mock_init.assert_called_once_with("test_dsn", environment="dev")
    mock_capture.assert_called_once_with(exc)


@patch.dict(os.environ, {"SENTRY_DSN": "test_dsn"})
@patch("sentry_sdk.init", side_effect=Exception("test init exception"))
@patch("sentry_sdk.capture_exception")
def test_sentry_capture_with_sentry_installed_and_init_fails(mock_capture, mock_init):
    from safe_init.sentry import sentry_capture

    assert sentry_capture(Exception("test exception")) is False
    mock_init.assert_called_once_with("test_dsn", environment="dev")
    mock_capture.assert_not_called()


@patch.dict(os.environ, {"SENTRY_DSN": "test_dsn"})
@patch("sentry_sdk.init")
@patch("sentry_sdk.capture_exception", side_effect=Exception("test capture exception"))
def test_sentry_capture_with_sentry_installed_and_capture_fails(mock_capture, mock_init):
    from safe_init.sentry import sentry_capture

    exc = Exception("test exception")
    assert sentry_capture(exc) is False
    mock_init.assert_called_once_with("test_dsn", environment="dev")
    mock_capture.assert_called_once_with(exc)


@patch.dict(os.environ, {"SENTRY_DSN": "test_dsn"})
@patch("sentry_sdk.init", side_effect=Exception("test init exception"))
@patch("sentry_sdk.capture_exception", side_effect=Exception("test capture exception"))
def test_sentry_capture_with_sentry_installed_and_both_init_and_capture_fail(mock_capture, mock_init):
    from safe_init.sentry import sentry_capture

    assert sentry_capture(Exception("test exception")) is False
    mock_init.assert_called_once_with("test_dsn", environment="dev")
    mock_capture.assert_not_called()


@patch.dict(os.environ, {"SENTRY_DSN": "test_dsn", "SAFE_INIT_ENV": "test_env"})
@patch("sentry_sdk.init")
@patch("sentry_sdk.capture_exception")
def test_sentry_capture_with_sentry_installed_and_custom_env(mock_capture, mock_init):
    from safe_init.sentry import sentry_capture

    exc = Exception("test exception")
    assert sentry_capture(exc) is True
    mock_init.assert_called_once_with("test_dsn", environment="test_env")
    mock_capture.assert_called_once_with(exc)


@patch.dict(os.environ, clear=True)
@patch("safe_init.sentry.log_warning")
def test_sentry_capture_with_sentry_not_installed(mock_warning):
    from safe_init.sentry import sentry_capture

    assert sentry_capture(Exception("test exception")) is False
    mock_warning.assert_called_once_with("Sentry is not installed")


@patch.dict(os.environ, {"SENTRY_DSN": ""})
@patch("safe_init.sentry.log_warning")
def test_sentry_capture_with_empty_sentry_dsn(mock_warning):
    from safe_init.sentry import sentry_capture

    assert sentry_capture(Exception("test exception")) is False
    mock_warning.assert_called_once_with("Sentry is not installed")


@patch.dict(os.environ, clear=True)
@patch("safe_init.sentry.log_warning")
def test_sentry_capture_with_none_sentry_dsn(mock_warning):
    from safe_init.sentry import sentry_capture

    assert sentry_capture(Exception("test exception")) is False
    mock_warning.assert_called_once_with("Sentry is not installed")


@patch.dict(os.environ, {"SENTRY_DSN": "test_dsn", "UNIT_TEST_SENTRY": "1"})
@patch("sentry_sdk.init")
@patch("sentry_sdk.push_scope")
@patch("sentry_sdk.capture_exception")
def test_sentry_capture_with_fingerprint(mock_capture, mock_push_scope, mock_init):
    mock_scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = mock_scope
    from safe_init.sentry import sentry_capture

    fingerprint = "test123"
    exc = Exception("test exception")
    assert sentry_capture(exc, fingerprint=fingerprint) is True
    mock_init.assert_called_once_with("test_dsn", environment="dev")
    mock_capture.assert_called_once_with(exc)
    mock_scope.set_tag.assert_not_called()
    assert mock_scope.fingerprint == fingerprint


@patch.dict(os.environ, {"SENTRY_DSN": "test_dsn", "UNIT_TEST_SENTRY": "1"})
@patch("sentry_sdk.init")
@patch("sentry_sdk.push_scope")
@patch("sentry_sdk.capture_exception")
def test_sentry_capture_with_tags(mock_capture, mock_push_scope, mock_init):
    mock_scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = mock_scope
    from safe_init.sentry import sentry_capture

    tags = {"t1": "value 1", "t2": "value 2"}
    exc = Exception("test exception")
    assert sentry_capture(exc, tags=tags) is True
    mock_init.assert_called_once_with("test_dsn", environment="dev")
    mock_capture.assert_called_once_with(exc)
    for key, value in tags.items():
        mock_scope.set_tag.assert_any_call(key, value)


@patch.dict(os.environ, {"SENTRY_DSN": "test_dsn", "UNIT_TEST_SENTRY": "1"})
@patch("sentry_sdk.init")
@patch("safe_init.sentry.log_warning")
@patch("sentry_sdk.push_scope")
@patch("sentry_sdk.capture_exception")
def test_sentry_capture_with_attachments(mock_capture, mock_push_scope, mock_log_warning, mock_init):
    mock_scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = mock_scope
    from safe_init.sentry import sentry_capture

    inner = {"t1": "value 1", "t2": "value 2"}
    outer = {"some_attachment": inner, "invalid_attachment": object()}
    exc = Exception("test exception")
    assert sentry_capture(exc, attachments=outer) is True
    mock_capture.assert_called_once_with(exc)
    mock_log_warning.assert_called_once_with(
        "Failed to serialize attachment to JSON, skipping", key="invalid_attachment"
    )
    mock_scope.add_attachment.assert_called_once_with(
        filename="some_attachment.json", bytes=json.dumps(inner).encode(), content_type="application/json"
    )


@patch.dict(os.environ, clear=True)
@patch("sentry_sdk.init")
def test_use_sentry_with_sentry_not_installed(mock_init):
    from safe_init.sentry import USE_SENTRY

    assert USE_SENTRY is False
