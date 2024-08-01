import json
import os
import unittest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from safe_init.secrets import (
    context_has_secrets_to_resolve,
    get_redis_client,
    get_secret_from_cache,
    get_secret_from_secrets_manager,
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

    def test_context_has_secrets_to_resolve_false(self):
        self.assertFalse(context_has_secrets_to_resolve())

    @patch("safe_init.secrets.get_secret_from_cache")
    @patch("safe_init.secrets.get_secret_from_secrets_manager")
    def test_resolve_secrets_success(self, mock_get_secret_from_secrets_manager, mock_get_secret_from_cache):
        with env(
            {
                "SECRET1_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1",
                "SECRET2_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2",
            }
        ):
            mock_get_secret_from_cache.side_effect = [None, "secret_value2"]
            mock_get_secret_from_secrets_manager.return_value = "secret_value1"

            secrets = resolve_secrets()

            self.assertEqual({"SECRET1": "secret_value1", "SECRET2": "secret_value2"}, secrets)
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1")
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2")
            mock_get_secret_from_secrets_manager.assert_called_once_with(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"
            )

    @patch("safe_init.secrets.get_secret_from_cache")
    @patch("safe_init.secrets.get_secret_from_secrets_manager")
    def test_resolve_secrets_failure(self, mock_get_secret_from_secrets_manager, mock_get_secret_from_cache):
        with env({"SECRET1_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"}):
            mock_get_secret_from_cache.return_value = None
            mock_get_secret_from_secrets_manager.side_effect = Exception("Failed to resolve secret")

            secrets = resolve_secrets()

            self.assertEqual({}, secrets)
            mock_get_secret_from_cache.assert_called_once_with(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"
            )
            mock_get_secret_from_secrets_manager.assert_called_once_with(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"
            )

    @patch("safe_init.secrets.redis.Redis")
    def test_get_redis_client(self, mock_redis):
        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        redis_client = get_redis_client()

        self.assertEqual(mock_redis_client, redis_client)
        mock_redis.assert_called_once_with(
            host="localhost",
            port="6379",
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
    @patch("safe_init.secrets.save_secret_in_cache")
    def test_get_secret_from_secrets_manager_success(self, mock_save_secret_in_cache, mock_get_secrets_manager_client):
        mock_secrets_manager_client = MagicMock()
        mock_secrets_manager_client.get_secret_value.return_value = {
            "SecretString": "secret_value",
            "VersionId": "version1",
        }
        mock_get_secrets_manager_client.return_value = mock_secrets_manager_client

        secret_value = get_secret_from_secrets_manager("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1")

        self.assertEqual("secret_value", secret_value)
        mock_secrets_manager_client.get_secret_value.assert_called_once_with(
            SecretId="arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"
        )
        mock_save_secret_in_cache.assert_called_once_with(
            "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1", "secret_value"
        )

    @patch("safe_init.secrets.get_secrets_manager_client")
    def test_get_secret_from_secrets_manager_not_found(self, mock_get_secrets_manager_client):
        mock_secrets_manager_client = MagicMock()
        mock_secrets_manager_client.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "GetSecretValue"
        )
        mock_get_secrets_manager_client.return_value = mock_secrets_manager_client

        secret_value = get_secret_from_secrets_manager("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1")

        self.assertIsNone(secret_value)
        mock_secrets_manager_client.get_secret_value.assert_called_once_with(
            SecretId="arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"
        )

    @patch("safe_init.secrets.get_secret_from_cache")
    @patch("safe_init.secrets.get_secret_from_secrets_manager")
    def test_resolve_json_secrets_success(self, mock_get_secret_from_secrets_manager, mock_get_secret_from_cache):
        with env(
            {
                "SECRET1_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1~key1",
                "SECRET2_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2~key2",
            }
        ):
            mock_get_secret_from_cache.side_effect = [None, json.dumps({"key2": "value2"})]
            mock_get_secret_from_secrets_manager.return_value = json.dumps({"key1": "value1"})

            secrets = resolve_secrets()

            self.assertEqual({"SECRET1": "value1", "SECRET2": "value2"}, secrets)
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1")
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2")
            mock_get_secret_from_secrets_manager.assert_called_once_with(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"
            )

    @patch("safe_init.secrets.get_secret_from_cache")
    @patch("safe_init.secrets.get_secret_from_secrets_manager")
    def test_resolve_secrets_with_common_prefix(self, mock_get_secret_from_secrets_manager, mock_get_secret_from_cache):
        with env(
            {
                "SAFE_INIT_SECRET_ARN_PREFIX": "arn:aws:secretsmanager:us-east-1:123456789012:",
                "SECRET1_SECRET_ARN": "secret:secret1",
                "SECRET2_SECRET_ARN": "secret:secret2",
            }
        ):
            mock_get_secret_from_cache.side_effect = [None, "secret_value2"]
            mock_get_secret_from_secrets_manager.return_value = "secret_value1"

            secrets = resolve_secrets()

            self.assertEqual({"SECRET1": "secret_value1", "SECRET2": "secret_value2"}, secrets)
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1")
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2")
            mock_get_secret_from_secrets_manager.assert_called_once_with(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"
            )

    @patch("safe_init.secrets.get_secret_from_cache")
    @patch("safe_init.secrets.get_secret_from_secrets_manager")
    def test_ignores_common_prefix_when_secrets_already_prefixed(
        self, mock_get_secret_from_secrets_manager, mock_get_secret_from_cache
    ):
        with env(
            {
                "SAFE_INIT_SECRET_ARN_PREFIX": "arn:aws:secretsmanager:us-east-1:123456789012:",
                "SECRET1_SECRET_ARN": "secret:secret1",
                "SECRET2_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2",
            }
        ):
            mock_get_secret_from_cache.return_value = None
            mock_get_secret_from_secrets_manager.side_effect = ["secret_value1", "secret_value2"]

            secrets = resolve_secrets()

            self.assertEqual({"SECRET1": "secret_value1", "SECRET2": "secret_value2"}, secrets)
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1")
            mock_get_secret_from_cache.assert_any_call("arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2")
            mock_get_secret_from_secrets_manager.assert_any_call(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret1"
            )
            mock_get_secret_from_secrets_manager.assert_any_call(
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret2"
            )
