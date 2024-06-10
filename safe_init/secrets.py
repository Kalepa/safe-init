import json
import os
from collections.abc import Mapping
from typing import TYPE_CHECKING

import boto3
import redis
from botocore.exceptions import ClientError

from safe_init.utils import bool_env

if TYPE_CHECKING:
    from boto3_type_annotations.secretsmanager import Client

from safe_init.safe_logging import log_debug, log_warning

SECRET_SUFFIX = os.getenv("SAFE_INIT_SECRET_ARN_SUFFIX", "_SECRET_ARN")
CACHE_TTL = int(os.getenv("SAFE_INIT_SECRET_CACHE_TTL", "1800"))  # default 30 minutes
CACHE_PREFIX = os.getenv("SAFE_INIT_SECRET_CACHE_PREFIX", "safe-init-secret::")
JSON_SECRET_SEPARATOR = "~"  # noqa: S105


def context_has_secrets_to_resolve() -> bool:
    """
    Returns whether the execution context has secrets to resolve.
    """
    return any(env_var.endswith(SECRET_SUFFIX) for env_var in os.environ.keys())  # noqa: SIM118


def resolve_secrets() -> Mapping[str, str | None]:
    """
    Resolves the secrets in the execution context and returns them as a dictionary.

    Returns:
        The resolved secrets as a dictionary.
    """
    secret_arns = {}
    for env_var, secret_arn in os.environ.items():
        if not env_var.endswith(SECRET_SUFFIX):
            continue
        secret_name = env_var[: -len(SECRET_SUFFIX)]
        secret_arns[secret_name] = secret_arn

    secrets = {}
    for secret_name, raw_secret_arn in secret_arns.items():
        try:
            secret_arn = raw_secret_arn
            if is_json_secret := JSON_SECRET_SEPARATOR in raw_secret_arn:
                secret_json_key = raw_secret_arn.split(JSON_SECRET_SEPARATOR, 1)[1]
                secret_arn = raw_secret_arn.split(JSON_SECRET_SEPARATOR, 1)[0]

            if not (secret_value := get_secret_from_cache(secret_arn)):
                secret_value = get_secret_from_secrets_manager(secret_arn)
            if secret_value:
                if not is_json_secret:
                    secrets[secret_name] = secret_value
                    continue
                secret_json = json.loads(secret_value)
                secrets[secret_name] = secret_json[secret_json_key]
        except Exception as e:
            if bool_env("SAFE_INIT_FAIL_ON_SECRET_RESOLUTION_ERROR"):
                raise
            log_warning("Failed to resolve secret", secret_arn=secret_arn, exc_info=e)

    log_debug("Resolved secrets", secrets=secrets.keys())

    return secrets


def get_redis_client() -> redis.Redis:
    if "_secrets_redis_client" not in globals() or not globals()["_secrets_redis_client"]:
        globals()["_secrets_redis_client"] = redis.Redis(
            host=os.getenv("SAFE_INIT_SECRET_CACHE_REDIS_HOST"),
            port=os.getenv("SAFE_INIT_SECRET_CACHE_REDIS_PORT"),
            db=int(os.getenv("SAFE_INIT_SECRET_CACHE_REDIS_DB", "0")),
            username=os.getenv("SAFE_INIT_SECRET_CACHE_REDIS_USERNAME"),
            password=os.getenv("SAFE_INIT_SECRET_CACHE_REDIS_PASSWORD"),
        )
    return globals()["_secrets_redis_client"]


def get_secrets_manager_client() -> "Client":
    if "_secrets_manager_client" not in globals() or not globals()["_secrets_manager_client"]:
        globals()["_secrets_manager_client"] = boto3.client("secretsmanager")
    return globals()["_secrets_manager_client"]


def is_secret_cache_enabled() -> bool:
    """
    Returns whether the secret cache is enabled and configured properly.

    Returns:
        True if the secret cache is enabled, False otherwise.
    """
    return bool(
        bool_env("SAFE_INIT_CACHE_SECRETS")
        and os.getenv("SAFE_INIT_SECRET_CACHE_REDIS_HOST")
        and os.getenv("SAFE_INIT_SECRET_CACHE_REDIS_PORT"),
    )


def get_secret_from_cache(secret_arn: str) -> str | None:
    """
    Retrieves the secret value from the cache.

    Args:
        secret_arn (str): The ARN of the secret to retrieve.

    Returns:
        The secret value if found in the cache, None otherwise.
    """
    if not is_secret_cache_enabled():
        log_debug("Secret caching is disabled", secret_arn=secret_arn)
        return None
    redis_client = get_redis_client()
    secret_value = redis_client.get(f"{CACHE_PREFIX}{secret_arn}")

    if secret_value:
        log_debug("Secret retrieved from cache", secret_arn=secret_arn)
        secret_value = secret_value.decode() if isinstance(secret_value, bytes) else secret_value

    return secret_value  # type: ignore[return-value]


def save_secret_in_cache(secret_arn: str, secret_value: str) -> None:
    """
    Saves the secret value in the cache.

    Args:
        secret_arn (str): The ARN of the secret to save.
        secret_value (str): The value of the secret to save.
    """
    if not is_secret_cache_enabled():
        log_debug("Secret caching is disabled, not saving", secret_arn=secret_arn)
        return
    redis_client = get_redis_client()
    redis_client.set(
        f"{CACHE_PREFIX}{secret_arn}",
        secret_value,
        ex=CACHE_TTL,
    )
    log_debug("Secret saved in cache", secret_arn=secret_arn)


def get_secret_from_secrets_manager(secret_arn: str) -> str | None:
    """
    Retrieves the secret value from Secrets Manager.

    Args:
        secret_arn (str): The ARN of the secret to retrieve.

    Returns:
        The secret value.
    """
    secrets_client = get_secrets_manager_client()
    try:
        secret = secrets_client.get_secret_value(SecretId=secret_arn)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            log_warning("Secret not found in Secrets Manager", secret_arn=secret_arn)
            return None
        raise

    secret_value = secret["SecretString"]
    log_debug("Secret retrieved from Secrets Manager", secret_arn=secret_arn, version_id=secret["VersionId"])

    save_secret_in_cache(secret_arn, secret_value)
    return secret_value
