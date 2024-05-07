import os

import pytest

from safe_init.utils import env


def test_env_updates_environment_variables():
    with env({"NEW_VAR": "NEW_VALUE"}):
        assert os.environ["NEW_VAR"] == "NEW_VALUE"


def test_env_removes_environment_variables():
    os.environ["VAR_TO_REMOVE"] = "VALUE"
    with env({"VAR_TO_REMOVE": None}):
        assert "VAR_TO_REMOVE" not in os.environ


def test_env_restores_original_environment_after_exit():
    os.environ["VAR_TO_RESTORE"] = "ORIGINAL_VALUE"
    with env({"VAR_TO_RESTORE": "NEW_VALUE"}):
        pass
    assert os.environ["VAR_TO_RESTORE"] == "ORIGINAL_VALUE"


def test_env_handles_multiple_variables():
    os.environ["VAR1"] = "ORIGINAL_VALUE1"
    os.environ["VAR2"] = "ORIGINAL_VALUE2"
    with env({"VAR1": "NEW_VALUE", "VAR2": None}):
        assert os.environ["VAR1"] == "NEW_VALUE"
        assert "VAR2" not in os.environ
    assert os.environ["VAR1"] == "ORIGINAL_VALUE1"
    assert os.environ["VAR2"] == "ORIGINAL_VALUE2"


def test_env_with_no_variables():
    original_env = dict(os.environ)
    with env({}):
        assert os.environ == original_env


def test_env_with_non_string_key_raises_error():
    with pytest.raises(TypeError):
        with env({1: "NEW_VALUE"}):
            pass
