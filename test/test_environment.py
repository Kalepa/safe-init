import json
import os
from unittest.mock import mock_open, patch

import pytest

from safe_init.environment import (
    ADDITIONAL_ENV_VARS_FILE,
    has_extra_env_vars,
    load_extra_env_vars,
)


@pytest.fixture
def set_env(monkeypatch):
    def _set_env(key, value):
        monkeypatch.setenv(key, value)

    return _set_env


def test_has_extra_env_vars_exists_non_empty_readable(set_env):
    with (
        patch("os.path.isfile", return_value=True) as mock_isfile,
        patch("os.path.getsize", return_value=10) as mock_getsize,
        patch("os.access", return_value=True) as mock_access,
    ):
        assert has_extra_env_vars() is True
        mock_isfile.assert_called_once_with(ADDITIONAL_ENV_VARS_FILE)
        mock_getsize.assert_called_once_with(ADDITIONAL_ENV_VARS_FILE)
        mock_access.assert_called_once_with(ADDITIONAL_ENV_VARS_FILE, os.R_OK)


def test_has_extra_env_vars_file_not_exists(set_env):
    with patch("os.path.isfile", return_value=False) as mock_isfile:
        assert has_extra_env_vars() is False
        mock_isfile.assert_called_once_with(ADDITIONAL_ENV_VARS_FILE)


def test_has_extra_env_vars_file_empty(set_env):
    with patch("os.path.isfile", return_value=True), patch("os.path.getsize", return_value=0) as mock_getsize:
        assert has_extra_env_vars() is False
        mock_getsize.assert_called_once_with(ADDITIONAL_ENV_VARS_FILE)


def test_has_extra_env_vars_file_not_readable(set_env):
    with (
        patch("os.path.isfile", return_value=True),
        patch("os.path.getsize", return_value=10),
        patch("os.access", return_value=False) as mock_access,
    ):
        assert has_extra_env_vars() is False
        mock_access.assert_called_once_with(ADDITIONAL_ENV_VARS_FILE, os.R_OK)


def test_has_extra_env_vars_exception_handling(set_env):
    with (
        patch("os.path.isfile", side_effect=OSError),
        patch("safe_init.error_utils.suppress_exceptions") as mock_decorator,
    ):
        assert has_extra_env_vars() is False


def test_load_extra_env_vars_success(set_env):
    mock_data = {"VAR1": "value1", "VAR2": "value2", "VAR3": None}
    mocked_json = json.dumps(mock_data)
    with (
        patch("builtins.open", mock_open(read_data=mocked_json)) as mock_file,
        patch("os.getenv", return_value=".env.json") as mock_getenv,
    ):
        with patch("json.load", return_value=mock_data) as mock_json_load:
            result = load_extra_env_vars()
            assert result == mock_data
            mock_file.assert_called_once_with(ADDITIONAL_ENV_VARS_FILE)
            mock_json_load.assert_called_once()


def test_load_extra_env_vars_file_not_found(set_env):
    with (
        patch("builtins.open", mock_open()) as mock_file,
        patch("json.load", side_effect=FileNotFoundError()),
        patch("safe_init.environment.log_error") as mock_log_error,
    ):
        result = load_extra_env_vars()
        assert result == {}
        mock_log_error.assert_called_once()
        mock_file.assert_called_once_with(ADDITIONAL_ENV_VARS_FILE)


def test_load_extra_env_vars_invalid_json(set_env):
    with (
        patch("builtins.open", mock_open(read_data="invalid json")),
        patch("json.load", side_effect=json.JSONDecodeError("Expecting value", "", 0)),
        patch("safe_init.environment.log_error") as mock_log_error,
    ):
        result = load_extra_env_vars()
        assert result == {}
        mock_log_error.assert_called_once()


def test_load_extra_env_vars_not_a_dict(set_env):
    mock_data = ["not", "a", "dict"]
    with (
        patch("builtins.open", mock_open(read_data=json.dumps(mock_data))),
        patch("json.load", return_value=mock_data),
        patch("safe_init.environment.log_error") as mock_log_error,
    ):
        result = load_extra_env_vars()
        assert result == {}
        mock_log_error.assert_called_once()


def test_load_extra_env_vars_non_string_keys(set_env):
    mock_data = {"VAR1": "value1", 2: "value2", "VAR3": "value3"}
    with (
        patch("builtins.open", mock_open(read_data=json.dumps(mock_data))),
        patch("json.load", return_value=mock_data),
        patch("safe_init.environment.log_error") as mock_log_error,
    ):
        result = load_extra_env_vars()
        expected = {"VAR1": "value1", "VAR3": "value3"}
        assert result == expected
        mock_log_error.assert_called_once()


def test_load_extra_env_vars_non_string_values_convertible(set_env):
    mock_data = {"VAR1": "value1", "VAR2": 123, "VAR3": None}
    with (
        patch("builtins.open", mock_open(read_data=json.dumps(mock_data))),
        patch("json.load", return_value=mock_data),
        patch("safe_init.environment.log_error") as mock_log_error,
        patch("safe_init.environment.log_warning") as mock_log_warning,
    ):
        result = load_extra_env_vars()
        expected = {"VAR1": "value1", "VAR2": "123", "VAR3": None}
        assert result == expected
        mock_log_error.assert_not_called()
        mock_log_warning.assert_called_once()


def test_load_extra_env_vars_mixed_invalid_keys_and_values(set_env):
    mock_data = {"VAR1": "value1", 2: 456, "VAR3": ["list"], "VAR4": "value4"}
    with (
        patch("builtins.open", mock_open(read_data=json.dumps(mock_data))),
        patch("json.load", return_value=mock_data),
        patch("safe_init.environment.log_error") as mock_log_error,
        patch("safe_init.environment.log_warning") as mock_log_warning,
    ):
        result = load_extra_env_vars()
        expected = {"VAR1": "value1", "VAR3": "['list']", "VAR4": "value4"}
        assert result == expected
        assert mock_log_error.call_count == 1
        mock_log_warning.assert_called_once()


def test_load_extra_env_vars_decorator_suppresses_exception(set_env):
    with (
        patch("builtins.open", side_effect=Exception("Unexpected error")),
        patch("safe_init.environment.log_error") as mock_log_error,
    ):
        result = load_extra_env_vars()
        assert result == {}
        mock_log_error.assert_called_once()


def test_load_extra_env_vars_empty_file(set_env):
    with patch("builtins.open", mock_open(read_data="{}")), patch("json.load", return_value={}) as mock_json_load:
        result = load_extra_env_vars()
        assert result == {}
        mock_json_load.assert_called_once()


def test_load_extra_env_vars_null_values(set_env):
    mock_data = {"VAR1": None, "VAR2": "value2", "VAR3": "value3"}
    with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))), patch("json.load", return_value=mock_data):
        result = load_extra_env_vars()
        assert result == mock_data


def test_load_extra_env_vars_with_extra_env_vars_file_env_var(set_env):
    with (
        patch("os.getenv", return_value="custom.env.json"),
        patch("builtins.open", mock_open(read_data='{"VAR1": "value1"}')),
        patch("json.load", return_value={"VAR1": "value1"}),
    ):
        result = load_extra_env_vars()
        assert result == {"VAR1": "value1"}
