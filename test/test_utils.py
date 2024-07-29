import os
from contextvars import ContextVar

import pytest

from safe_init.utils import bool_env, env, get_contextvar_named


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


@pytest.mark.parametrize(
    "env_var, expected",
    [
        ("1", True),
        ("true", True),
        ("yes", True),
        ("on", True),
        ("y", True),
        ("0", False),
        ("false", False),
        ("no", False),
        ("off", False),
        ("n", False),
        ("", False),
        ("random", False),
        ("True", True),
        ("Yes", True),
        ("On", True),
        ("Y", True),
        (" 1 ", True),
        (" true ", True),
        (" yes ", True),
        (" on ", True),
        (" y ", True),
        (" 0 ", False),
        (" false ", False),
        (" no ", False),
        (" off ", False),
        (" n ", False),
        (" ", False),
        ("onn", False),
    ],
)
def test_bool_env(monkeypatch, env_var, expected):
    monkeypatch.setenv("TEST_VAR", env_var)
    assert bool_env("TEST_VAR") == expected


def test_returns_value_if_contextvar_exists():
    var = ContextVar("test_var", default="default_value")
    var.set("test_value")
    assert get_contextvar_named("test_var") == "test_value"


def test_returns_none_if_contextvar_does_not_exist():
    assert get_contextvar_named("non_existent_var") is None


def test_returns_none_if_contextvar_has_no_value():
    var = ContextVar("empty_test_var")
    assert get_contextvar_named("empty_test_var") is None
