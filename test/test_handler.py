import os
import random
import sys
from unittest.mock import ANY, MagicMock, patch


class TestHandler:
    @patch("safe_init.slack.slack_notify")
    @patch("test.test_module.test_handler")
    def test_slack_notification_on_uninitialized_sentry(self, mock_handler, mock_slack):
        os.environ["SAFE_INIT_HANDLER"] = "test.test_module.test_handler"
        os.environ["SAFE_INIT_NO_DETECT_INIT_ISSUES"] = "true"
        from safe_init.handler import handler

        handler()
        mock_slack.assert_called_once_with(
            "Detected missing Sentry initialization",
            ANY,
            handler_name=os.environ["SAFE_INIT_HANDLER"],
            message_title="Sentry detector warning",
        )
        del os.environ["SAFE_INIT_HANDLER"]

    @patch("sentry_sdk.get_client", MagicMock())
    @patch("safe_init.slack.slack_notify")
    @patch("test.test_module.test_handler")
    def test_no_slack_notification_on_uninitialized_sentry(self, mock_handler, mock_slack):
        os.environ["SAFE_INIT_HANDLER"] = "test.test_module.test_handler"
        os.environ["SAFE_INIT_NO_DETECT_INIT_ISSUES"] = "true"
        from safe_init.handler import handler

        handler()
        mock_slack.assert_not_called()

    @patch("safe_init.handler.log_warning")
    @patch("safe_init.handler.slack_notify")
    @patch("safe_init.handler._get_execution_hash")
    def test_pre_import_hook_no_detect_init_issues(self, mock_get_execution_hash, mock_slack_notify, mock_log_warning):
        os.environ["SAFE_INIT_NO_DETECT_INIT_ISSUES"] = "true"
        from safe_init.handler import _pre_import_hook

        _pre_import_hook("test_handler")
        mock_get_execution_hash.assert_not_called()
        mock_slack_notify.assert_not_called()
        mock_log_warning.assert_not_called()

    @patch.dict(
        os.environ,
        {
            "SAFE_INIT_ENV": "prod",
            "SAFE_INIT_NO_DETECT_INIT_ISSUES": "",
            "SAFE_INIT_NOTIFY_SLACK_ON_INIT_ISSUES": "true",
        },
    )
    @patch("safe_init.handler.log_warning")
    @patch("safe_init.handler.slack_notify")
    @patch("safe_init.handler._get_execution_hash")
    def test_pre_import_hook_execution_hash_exists(self, mock_get_execution_hash, mock_slack_notify, mock_log_warning):
        mock_get_execution_hash.return_value = "lol420"
        if os.path.exists("/tmp/safe_init.handler__lol420__"):
            os.remove("/tmp/safe_init.handler__lol420__")
        if os.path.exists("/tmp/safe_init.handler__lol420__imported__"):
            os.remove("/tmp/safe_init.handler__lol420__imported__")

        from safe_init.handler import _pre_import_hook

        _pre_import_hook("test_handler")
        mock_slack_notify.assert_not_called()

        _pre_import_hook("test_handler")
        mock_slack_notify.assert_called_once()
        mock_log_warning.assert_called_once()

    @patch.dict(
        os.environ,
        {"SAFE_INIT_ENV": "prod", "SAFE_INIT_NO_DETECT_INIT_ISSUES": "", "SAFE_INIT_NOTIFY_SLACK_ON_INIT_ISSUES": ""},
    )
    @patch("safe_init.handler.log_warning")
    @patch("safe_init.handler.slack_notify")
    @patch("safe_init.handler._get_execution_hash")
    def test_pre_import_hook_execution_hash_exists_no_slack(
        self, mock_get_execution_hash, mock_slack_notify, mock_log_warning
    ):
        mock_get_execution_hash.return_value = "lol420"
        if os.path.exists("/tmp/safe_init.handler__lol420__"):
            os.remove("/tmp/safe_init.handler__lol420__")
        if os.path.exists("/tmp/safe_init.handler__lol420__imported__"):
            os.remove("/tmp/safe_init.handler__lol420__imported__")

        from safe_init.handler import _pre_import_hook

        _pre_import_hook("test_handler")
        mock_slack_notify.assert_not_called()

        _pre_import_hook("test_handler")
        mock_slack_notify.assert_not_called()
        mock_log_warning.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "SAFE_INIT_ENV": "prod",
            "SAFE_INIT_NO_DETECT_INIT_ISSUES": "",
            "SAFE_INIT_NOTIFY_SLACK_ON_INIT_ISSUES": "true",
        },
    )
    @patch("safe_init.handler.log_warning")
    @patch("safe_init.handler.slack_notify")
    @patch("safe_init.handler._get_execution_hash")
    def test_pre_import_hook_multiple_executions(self, mock_get_execution_hash, mock_slack_notify, mock_log_warning):
        mock_get_execution_hash.return_value = "lol420"
        if os.path.exists("/tmp/safe_init.handler__lol420__"):
            os.remove("/tmp/safe_init.handler__lol420__")
        if os.path.exists("/tmp/safe_init.handler__lol420__imported__"):
            os.remove("/tmp/safe_init.handler__lol420__imported__")

        from safe_init.handler import _post_import_hook, _pre_import_hook

        _pre_import_hook("test_handler")
        mock_slack_notify.assert_not_called()

        _pre_import_hook("test_handler")
        assert mock_slack_notify.call_count == 1
        _post_import_hook("test_handler")

        mock_log_warning.assert_called_once()

        mock_slack_notify.reset_mock()
        mock_log_warning.reset_mock()

        _pre_import_hook("test_handler")
        mock_slack_notify.assert_not_called()
        mock_log_warning.assert_called_once()
        assert mock_log_warning.call_args[0][0] == "Import hook repeated despite previous successful initialization"

    @patch.dict(
        os.environ,
        {
            "SAFE_INIT_ENV": "prod",
            "SAFE_INIT_NO_DETECT_INIT_ISSUES": "",
            "SAFE_INIT_NOTIFY_SLACK_ON_INIT_ISSUES": "true",
        },
    )
    @patch("safe_init.handler.slack_notify")
    @patch("safe_init.handler._get_execution_hash")
    def test_pre_import_hook_execution_hash_not_exists(self, mock_get_execution_hash, mock_slack_notify):
        mock_get_execution_hash.return_value = random.randint(1, 100000)
        from safe_init.handler import _pre_import_hook

        _pre_import_hook("test_handler")
        mock_slack_notify.assert_not_called()


class TestRefreshSecretsAfterRestore:
    @patch.dict(os.environ, {"AWS_LAMBDA_INITIALIZATION_TYPE": "on-demand"})
    def test_other_initialization_types_get_the_handler_unchanged(self):
        from safe_init.handler import _refresh_secrets_after_restore

        func = MagicMock()
        with patch.dict(sys.modules, {"snapshot_restore_py": MagicMock()}) as modules:
            assert _refresh_secrets_after_restore(func, {}, {}) is func
            modules["snapshot_restore_py"].register_after_restore.assert_not_called()

    @patch.dict(os.environ, {"AWS_LAMBDA_INITIALIZATION_TYPE": "snap-start"})
    @patch("safe_init.handler.reset_clients")
    @patch("safe_init.handler.resolve_secrets")
    def test_first_invocation_after_restore_resolves_secrets_again(self, mock_resolve, mock_reset_clients):
        from safe_init.handler import _refresh_secrets_after_restore

        hooks = []
        env_vars = {"DB_PASSWORD": "old", "PLAIN": "extra"}
        mock_resolve.return_value = {"DB_PASSWORD": "new", "PLAIN": "secret"}
        func = MagicMock(__name__="handler")
        with patch.dict(sys.modules, {"snapshot_restore_py": MagicMock(register_after_restore=hooks.append)}):
            wrapped = _refresh_secrets_after_restore(func, env_vars, {"PLAIN": "extra"})

        wrapped("event", "context")
        mock_resolve.assert_not_called()

        hooks[0]()
        mock_reset_clients.assert_called_once()
        wrapped("event", "context")
        wrapped("event", "context")

        mock_resolve.assert_called_once_with({"PLAIN": "extra"})
        assert env_vars == {"DB_PASSWORD": "new", "PLAIN": "extra"}
        assert func.call_count == 3

    @patch.dict(os.environ, {"AWS_LAMBDA_INITIALIZATION_TYPE": "snap-start"})
    @patch("safe_init.handler.reset_clients", MagicMock())
    @patch("safe_init.handler.resolve_secrets", side_effect=RuntimeError("Secrets Manager is down"))
    def test_failed_refresh_keeps_the_snapshot_values(self, mock_resolve):
        from safe_init.handler import _refresh_secrets_after_restore

        hooks = []
        env_vars = {"DB_PASSWORD": "old"}
        func = MagicMock(__name__="handler")
        with patch.dict(sys.modules, {"snapshot_restore_py": MagicMock(register_after_restore=hooks.append)}):
            wrapped = _refresh_secrets_after_restore(func, env_vars, {})

        hooks[0]()
        wrapped("event", "context")

        assert env_vars == {"DB_PASSWORD": "old"}
        func.assert_called_once_with("event", "context")
