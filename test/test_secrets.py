import json
import os
import unittest
from unittest.mock import ANY, MagicMock, patch

from botocore.exceptions import ClientError

from safe_init.secrets import (
    MAX_SECRETS_PER_BATCH,
    SecretResolutionError,
    context_has_secrets_to_resolve,
    get_redis_client,
    get_secret_from_cache,
    get_secrets_from_secrets_manager,
    get_secrets_manager_client,
    is_secret_cache_enabled,
    resolve_secrets,
    save_secret_in_cache,
)
from safe_init.utils import env

TEST_ENV_VARS = {
    "SAFE_INIT_SECRET_SUFFIX": "_SECRET_ARN",
    "SAFE_INIT_SECRET_CACHE_TTL": "1800",
    "SAFE_INIT_SECRET_CACHE_PREFIX": "safe-init-secret::",
    "SAFE_INIT_FAIL_ON_SECRET_RESOLUTION_ERROR": "false",
    "SAFE_INIT_CACHE_SECRETS": "true",
    "SAFE_INIT_SECRET_CACHE_REDIS_HOST": "localhost",
    "SAFE_INIT_SECRET_CACHE_REDIS_PORT": "6379",
    "SAFE_INIT_SECRET_CACHE_REDIS_DB": "0",
    "SAFE_INIT_SECRET_CACHE_REDIS_USERNAME": "username",
    "SAFE_INIT_SECRET_CACHE_REDIS_PASSWORD": "password",
}


class TestSecretResolution(unittest.TestCase):
    def setUp(self):
        for key, value in TEST_ENV_VARS.items():
            os.environ[key] = value

    def tearDown(self):
        for key in TEST_ENV_VARS.keys():
            os.environ.pop(key, None)

    def test_context_has_secrets_to_resolve_true(self):
        with env({"SECRET1_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"}):
            self.assertTrue(context_has_secrets_to_resolve())

    def test_context_has_secrets_to_resolve_true_with_extra_env_vars(self):
        self.assertFalse(context_has_secrets_to_resolve())
        self.assertTrue(
            context_has_secrets_to_resolve(
                {"SECRET1_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"}
            )
        )

    def test_context_has_secrets_to_resolve_false(self):
        self.assertFalse(context_has_secrets_to_resolve())

    @patch("safe_init.secrets.get_secret_from_cache")
    @patch("safe_init.secrets.save_secret_in_cache")
    @patch("safe_init.secrets.get_secrets_from_secrets_manager")
    def test_resolve_secrets_success(
        self, mock_get_secrets_from_secrets_manager, mock_save_secret_in_cache, mock_get_secret_from_cache
    ):
        with env(
            {
                "SECRET1_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1",
                "SECRET2_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2",
            }
        ):
            mock_get_secret_from_cache.side_effect = [None, "secret_value2"]
            mock_get_secrets_from_secrets_manager.return_value = (
                {"arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1": "secret_value1"},
                None,
            )

            secrets = resolve_secrets()

            self.assertEqual({"SECRET1": "secret_value1", "SECRET2": "secret_value2"}, secrets)
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1")
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2")
            mock_get_secrets_from_secrets_manager.assert_called_once_with(
                ["arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"]
            )
            mock_save_secret_in_cache.assert_called_once_with(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1", "secret_value1"
            )

    @patch("safe_init.secrets.get_secret_from_cache")
    @patch("safe_init.secrets.save_secret_in_cache")
    @patch("safe_init.secrets.get_secrets_from_secrets_manager")
    def test_resolve_secrets_success_with_extra_env_vars(
        self, mock_get_secrets_from_secrets_manager, mock_save_secret_in_cache, mock_get_secret_from_cache
    ):
        with env(
            {
                "SECRET1_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1",
            }
        ):
            mock_get_secret_from_cache.side_effect = [None, None]
            mock_get_secrets_from_secrets_manager.return_value = (
                {
                    "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1": "secret_value1",
                    "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret-extra": "secret_value_extra",
                },
                None,
            )

            secrets = resolve_secrets(
                {"SECRET_EXTRA_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret-extra"}
            )

            self.assertEqual({"SECRET1": "secret_value1", "SECRET_EXTRA": "secret_value_extra"}, secrets)
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1")
            mock_get_secret_from_cache.assert_any_call(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret-extra"
            )
            mock_get_secrets_from_secrets_manager.assert_called_once_with(
                [
                    "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1",
                    "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret-extra",
                ]
            )
            mock_save_secret_in_cache.assert_any_call(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1", "secret_value1"
            )
            mock_save_secret_in_cache.assert_any_call(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret-extra", "secret_value_extra"
            )

    @patch("safe_init.secrets.get_secret_from_cache")
    @patch("safe_init.secrets.save_secret_in_cache")
    @patch("safe_init.secrets.get_secrets_from_secrets_manager")
    def test_resolve_secrets_keeps_partially_retrieved_secrets(
        self, mock_get_secrets_from_secrets_manager, mock_save_secret_in_cache, mock_get_secret_from_cache
    ):
        with env(
            {
                "SECRET1_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1",
                "SECRET2_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2",
            }
        ):
            mock_get_secret_from_cache.return_value = None
            mock_get_secrets_from_secrets_manager.return_value = (
                {"arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1": "secret_value1"},
                ["arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2"],
            )

            secrets = resolve_secrets()

            self.assertEqual({"SECRET1": "secret_value1"}, secrets)
            mock_save_secret_in_cache.assert_called_once_with(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1", "secret_value1"
            )

    @patch("safe_init.secrets.get_secret_from_cache")
    @patch("safe_init.secrets.save_secret_in_cache")
    @patch("safe_init.secrets.get_secrets_from_secrets_manager")
    def test_resolve_secrets_partial_failure_raises_when_configured_to_fail(
        self, mock_get_secrets_from_secrets_manager, mock_save_secret_in_cache, mock_get_secret_from_cache
    ):
        with env(
            {
                "SAFE_INIT_FAIL_ON_SECRET_RESOLUTION_ERROR": "true",
                "SECRET1_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1",
                "SECRET2_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2",
            }
        ):
            mock_get_secret_from_cache.return_value = None
            mock_get_secrets_from_secrets_manager.return_value = (
                {"arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1": "secret_value1"},
                ["arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2"],
            )

            with self.assertRaises(SecretResolutionError):
                resolve_secrets()

            mock_save_secret_in_cache.assert_called_once_with(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1", "secret_value1"
            )

    @patch("safe_init.secrets.get_secret_from_cache")
    @patch("safe_init.secrets.get_secrets_from_secrets_manager")
    def test_resolve_secrets_global_failure(self, mock_get_secrets_from_secrets_manager, mock_get_secret_from_cache):
        with env({"SECRET1_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"}):
            mock_get_secret_from_cache.return_value = None
            mock_get_secrets_from_secrets_manager.side_effect = Exception("Failed to resolve secret")

            secrets = resolve_secrets()

            self.assertEqual({}, secrets)
            mock_get_secret_from_cache.assert_called_once_with(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"
            )
            mock_get_secrets_from_secrets_manager.assert_called_once_with(
                ["arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"]
            )

    @patch("safe_init.secrets.redis.Redis")
    def test_get_redis_client(self, mock_redis):
        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        redis_client = get_redis_client()

        self.assertEqual(mock_redis_client, redis_client)
        mock_redis.assert_called_once_with(
            host="localhost",
            port=6379,
            db=0,
            username="username",
            password="password",
        )

    @patch("safe_init.secrets.boto3.client")
    def test_get_secrets_manager_client(self, mock_boto3_client):
        mock_secrets_manager_client = MagicMock()
        mock_boto3_client.return_value = mock_secrets_manager_client

        secrets_manager_client = get_secrets_manager_client()

        self.assertEqual(mock_secrets_manager_client, secrets_manager_client)
        mock_boto3_client.assert_called_once_with("secretsmanager")

    def test_is_secret_cache_enabled_true(self):
        self.assertTrue(is_secret_cache_enabled())

    def test_is_secret_cache_enabled_false(self):
        os.environ["SAFE_INIT_CACHE_SECRETS"] = "false"
        self.assertFalse(is_secret_cache_enabled())

    @patch("safe_init.secrets.get_redis_client")
    def test_get_secret_from_cache_found(self, mock_get_redis_client):
        mock_redis_client = MagicMock()
        mock_redis_client.get.return_value = b"secret_value"
        mock_get_redis_client.return_value = mock_redis_client

        secret_value = get_secret_from_cache("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1")

        self.assertEqual("secret_value", secret_value)
        mock_redis_client.get.assert_called_once_with(
            "safe-init-secret::arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"
        )

    @patch("safe_init.secrets.get_redis_client")
    def test_get_secret_from_cache_not_found(self, mock_get_redis_client):
        mock_redis_client = MagicMock()
        mock_redis_client.get.return_value = None
        mock_get_redis_client.return_value = mock_redis_client

        secret_value = get_secret_from_cache("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1")

        self.assertIsNone(secret_value)
        mock_redis_client.get.assert_called_once_with(
            "safe-init-secret::arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"
        )

    @patch("safe_init.secrets.get_redis_client")
    @patch("safe_init.error_utils.log_error")
    def test_get_secret_from_cache_does_not_throw(self, mock_log_error, mock_get_redis_client):
        mock_redis_client = MagicMock()
        mock_redis_client.get.side_effect = Exception("Failed to get secret from cache")
        mock_get_redis_client.return_value = mock_redis_client

        secret_value = get_secret_from_cache("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1")

        self.assertIsNone(secret_value)
        mock_redis_client.get.assert_called_once_with(
            "safe-init-secret::arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"
        )
        mock_log_error.assert_called_once()
        args, kwargs = mock_log_error.call_args
        assert "Suppressed exception in get_secret_from_cache" in args[0]

    @patch("safe_init.secrets.get_redis_client")
    def test_save_secret_in_cache(self, mock_get_redis_client):
        mock_redis_client = MagicMock()
        mock_get_redis_client.return_value = mock_redis_client

        save_secret_in_cache("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1", "secret_value")

        mock_redis_client.set.assert_called_once_with(
            "safe-init-secret::arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1",
            "secret_value",
            ex=1800,
        )

    @patch("safe_init.secrets.get_secrets_manager_client")
    def test_get_secret_from_secrets_manager_success(self, mock_get_secrets_manager_client):
        mock_secrets_manager_client = MagicMock()
        mock_secrets_manager_client.batch_get_secret_value.return_value = {
            "SecretValues": [
                {
                    "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1",
                    "SecretString": "secret_value",
                    "VersionId": "version1",
                }
            ]
        }
        mock_get_secrets_manager_client.return_value = mock_secrets_manager_client

        secret_values, errors = get_secrets_from_secrets_manager(
            ["arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"]
        )

        assert errors == []
        self.assertEqual("secret_value", secret_values["arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"])
        mock_secrets_manager_client.batch_get_secret_value.assert_called_once_with(
            SecretIdList=["arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"]
        )

    @patch("safe_init.secrets.get_secrets_manager_client")
    def test_get_secret_from_secrets_manager_not_found(self, mock_get_secrets_manager_client):
        mock_secrets_manager_client = MagicMock()
        mock_secrets_manager_client.batch_get_secret_value.return_value = {
            "SecretValues": [],
            "Errors": [
                {
                    "SecretId": "arn:aws:secretsmanager:us-east-1:123456789012:secret1",
                    "ErrorCode": "ResourceNotFoundException",
                    "Message": "Secret not found",
                }
            ],
        }
        mock_get_secrets_manager_client.return_value = mock_secrets_manager_client

        secret_values, errors = get_secrets_from_secrets_manager(
            ["arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"]
        )

        assert secret_values == {}
        assert errors == []
        mock_secrets_manager_client.batch_get_secret_value.assert_called_once_with(
            SecretIdList=["arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"]
        )

    @patch("safe_init.secrets.get_secrets_manager_client")
    def test_get_secret_from_secrets_manager_splits_into_batches(self, mock_get_secrets_manager_client):
        arns = [
            f"arn:aws:secretsmanager:us-east-1:123456789012:secret:secret{i}"
            for i in range(2 * MAX_SECRETS_PER_BATCH + 5)
        ]
        mock_secrets_manager_client = MagicMock()
        mock_secrets_manager_client.batch_get_secret_value.side_effect = lambda **kwargs: {
            "SecretValues": [{"ARN": arn, "SecretString": f"value-of-{arn}"} for arn in kwargs["SecretIdList"]]
        }
        mock_get_secrets_manager_client.return_value = mock_secrets_manager_client

        secret_values, errors = get_secrets_from_secrets_manager(arns)

        self.assertEqual([], errors)
        self.assertEqual({arn: f"value-of-{arn}" for arn in arns}, secret_values)
        self.assertEqual(
            [MAX_SECRETS_PER_BATCH, MAX_SECRETS_PER_BATCH, 5],
            [
                len(call.kwargs["SecretIdList"])
                for call in mock_secrets_manager_client.batch_get_secret_value.call_args_list
            ],
        )

    @patch("safe_init.secrets.get_secrets_manager_client")
    def test_get_secret_from_secrets_manager_no_secrets(self, mock_get_secrets_manager_client):
        mock_secrets_manager_client = MagicMock()
        mock_get_secrets_manager_client.return_value = mock_secrets_manager_client

        secret_values, errors = get_secrets_from_secrets_manager([])

        assert secret_values == {}
        assert errors == []
        mock_secrets_manager_client.batch_get_secret_value.assert_not_called()

    @patch("safe_init.secrets.log_error")
    @patch("safe_init.secrets.get_secrets_manager_client")
    def test_get_secret_from_secrets_manager_failed_batch_does_not_affect_others(
        self, mock_get_secrets_manager_client, mock_log_error
    ):
        arns = [
            f"arn:aws:secretsmanager:us-east-1:123456789012:secret:secret{i}~key"
            for i in range(MAX_SECRETS_PER_BATCH + 5)
        ]
        failed_arns, fetched_arns = arns[:MAX_SECRETS_PER_BATCH], arns[MAX_SECRETS_PER_BATCH:]
        error = ClientError({"Error": {"Code": "InvalidParameterException"}}, "BatchGetSecretValue")
        mock_secrets_manager_client = MagicMock()
        mock_secrets_manager_client.batch_get_secret_value.side_effect = [
            error,
            {
                "SecretValues": [
                    {"ARN": arn.removesuffix("~key"), "SecretString": json.dumps({"key": "secret_value"})}
                    for arn in fetched_arns
                ]
            },
        ]
        mock_get_secrets_manager_client.return_value = mock_secrets_manager_client

        secret_values, errors = get_secrets_from_secrets_manager(arns)

        self.assertEqual(failed_arns, errors)
        self.assertEqual(set(fetched_arns), set(secret_values))
        self.assertEqual(
            {"error": ANY, "secret_arns": [arn.removesuffix("~key") for arn in failed_arns]},
            mock_log_error.call_args.kwargs,
        )

    def test_secret_values_are_never_logged(self):
        canary = "the-value-of-the-secret"
        arns = {
            "SECRET1_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1",
            "SECRET2_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2~missing_key",
        }
        mock_secrets_manager_client = MagicMock()
        mock_secrets_manager_client.batch_get_secret_value.return_value = {
            "SecretValues": [
                {"ARN": arns["SECRET1_SECRET_ARN"], "SecretString": canary},
                {"ARN": arns["SECRET2_SECRET_ARN"].removesuffix("~missing_key"), "SecretString": "{}"},
            ],
            "Errors": [
                {
                    "SecretId": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret3",
                    "ErrorCode": "AccessDeniedException",
                    "Message": "Access denied",
                }
            ],
        }

        with (
            env(arns),
            patch("safe_init.secrets.get_secret_from_cache", return_value=None),
            patch("safe_init.secrets.save_secret_in_cache"),
            patch("safe_init.secrets.get_secrets_manager_client", return_value=mock_secrets_manager_client),
            patch("safe_init.secrets.log_debug") as mock_log_debug,
            patch("safe_init.secrets.log_warning") as mock_log_warning,
            patch("safe_init.secrets.log_error") as mock_log_error,
        ):
            resolve_secrets()

        logged_calls = mock_log_debug.call_args_list + mock_log_warning.call_args_list + mock_log_error.call_args_list
        assert logged_calls
        for call in logged_calls:
            # A traceback renders the local variables of every frame, which hold the values of the secrets
            assert "exc_info" not in call.kwargs, call
            assert canary not in repr(call.args) + repr(call.kwargs), call

    @patch("safe_init.secrets.get_secrets_manager_client")
    def test_get_secret_from_secrets_manager_deduplicates_json_secret_arns(self, mock_get_secrets_manager_client):
        arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"
        secret_string = json.dumps({"key1": "value1", "key2": "value2"})
        mock_secrets_manager_client = MagicMock()
        mock_secrets_manager_client.batch_get_secret_value.return_value = {
            "SecretValues": [{"ARN": arn, "SecretString": secret_string}]
        }
        mock_get_secrets_manager_client.return_value = mock_secrets_manager_client

        secret_values, errors = get_secrets_from_secrets_manager([f"{arn}~key1", f"{arn}~key2"])

        assert errors == []
        assert secret_values == {f"{arn}~key1": secret_string, f"{arn}~key2": secret_string}
        mock_secrets_manager_client.batch_get_secret_value.assert_called_once_with(SecretIdList=[arn])

    @patch("safe_init.secrets.get_secret_from_cache")
    @patch("safe_init.secrets.save_secret_in_cache")
    @patch("safe_init.secrets.get_secrets_from_secrets_manager")
    def test_resolve_json_secrets_success(
        self, mock_get_secrets_from_secrets_manager, mock_save_secret_in_cache, mock_get_secret_from_cache
    ):
        with env(
            {
                "SECRET1_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1~key1",
                "SECRET2_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2~key2",
            }
        ):
            mock_get_secret_from_cache.side_effect = [None, json.dumps({"key2": "value2"})]
            mock_get_secrets_from_secrets_manager.return_value = (
                {"arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1~key1": json.dumps({"key1": "value1"})},
                None,
            )

            secrets = resolve_secrets()

            self.assertEqual({"SECRET1": "value1", "SECRET2": "value2"}, secrets)
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1")
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2")
            mock_get_secrets_from_secrets_manager.assert_called_once_with(
                ["arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1~key1"]
            )

    @patch("safe_init.secrets.get_secret_from_cache")
    @patch("safe_init.secrets.save_secret_in_cache")
    @patch("safe_init.secrets.get_secrets_from_secrets_manager")
    def test_resolve_secrets_with_common_prefix(
        self, mock_get_secrets_from_secrets_manager, mock_save_secret_in_cache, mock_get_secret_from_cache
    ):
        with env(
            {
                "SAFE_INIT_SECRET_ARN_PREFIX": "arn:aws:secretsmanager:us-east-1:123456789012:",
                "SECRET1_SECRET_ARN": "secret:secret1",
                "SECRET2_SECRET_ARN": "secret:secret2",
            }
        ):
            mock_get_secret_from_cache.side_effect = [None, "secret_value2"]
            mock_get_secrets_from_secrets_manager.return_value = (
                {"arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1": "secret_value1"},
                None,
            )

            secrets = resolve_secrets()

            self.assertEqual({"SECRET1": "secret_value1", "SECRET2": "secret_value2"}, secrets)
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1")
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2")
            mock_get_secrets_from_secrets_manager.assert_called_once_with(
                ["arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"]
            )
            mock_save_secret_in_cache.assert_called_once_with(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1", "secret_value1"
            )

    @patch("safe_init.secrets.get_secret_from_cache")
    @patch("safe_init.secrets.save_secret_in_cache")
    @patch("safe_init.secrets.get_secrets_from_secrets_manager")
    def test_ignores_common_prefix_when_secrets_already_prefixed(
        self, mock_get_secrets_from_secrets_manager, mock_save_secret_in_cache, mock_get_secret_from_cache
    ):
        with env(
            {
                "SAFE_INIT_SECRET_ARN_PREFIX": "arn:aws:secretsmanager:us-east-1:123456789012:",
                "SECRET1_SECRET_ARN": "secret:secret1",
                "SECRET2_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2",
            }
        ):
            mock_get_secret_from_cache.return_value = None
            mock_get_secrets_from_secrets_manager.return_value = (
                {
                    "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1": "secret_value1",
                    "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2": "secret_value2",
                },
                None,
            )

            secrets = resolve_secrets()

            self.assertEqual({"SECRET1": "secret_value1", "SECRET2": "secret_value2"}, secrets)
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1")
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2")
            mock_get_secrets_from_secrets_manager.assert_any_call(
                [
                    "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1",
                    "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2",
                ]
            )
            mock_save_secret_in_cache.assert_any_call(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1", "secret_value1"
            )
