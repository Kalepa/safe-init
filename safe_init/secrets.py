import json
import os
from collections.abc import Mapping
from typing import TYPE_CHECKING

import boto3
import redis
from botocore.exceptions import ClientError

from safe_init.error_utils import suppress_exceptions
from safe_init.utils import bool_env

if TYPE_CHECKING:
    from boto3_type_annotations.secretsmanager import Client

from safe_init.safe_logging import log_debug, log_error, log_warning

SECRET_SUFFIX = os.getenv("SAFE_INIT_SECRET_SUFFIX", os.getenv("SAFE_INIT_SECRET_ARN_SUFFIX", "_SECRET_ARN"))
CACHE_TTL = int(os.getenv("SAFE_INIT_SECRET_CACHE_TTL", "1800"))  # default 30 minutes
CACHE_PREFIX = os.getenv("SAFE_INIT_SECRET_CACHE_PREFIX", "safe-init-secret::")
JSON_SECRET_SEPARATOR = "~"  # noqa: S105


class SecretResolutionError(Exception):
    """
    Custom exception raised when secret resolution fails.
    """

    def __init__(self, message: str, errors: list[str]) -> None:
        super().__init__(message)
        self.errors = errors if errors is not None else []


def context_has_secrets_to_resolve(extra_env_vars: Mapping[str, str | None] | None = None) -> bool:
    """
    Returns whether the execution context has secrets to resolve.

    Args:
        extra_env_vars (Mapping[str, str] | None): Additional environment variables to consider.
    """
    env_keys = os.environ.keys() | (extra_env_vars.keys() if extra_env_vars else set())
    return any(env_var.endswith(SECRET_SUFFIX) for env_var in env_keys)


def resolve_secrets(extra_env_vars: Mapping[str, str | None] | None = None) -> Mapping[str, str | None]:
    """
    Resolves the secrets in the execution context and returns them as a dictionary.

    Args:
        extra_env_vars (Mapping[str, str] | None): Additional environment variables to consider.

    Returns:
        The resolved secrets as a dictionary.
    """
    common_secret_arn_prefix = os.getenv("SAFE_INIT_SECRET_ARN_PREFIX")
    secret_arns = gather_secret_arns(common_secret_arn_prefix, extra_env_vars)

    # Try to get secret values from Redis cache and identify secrets that are not in cache
    secrets, secrets_not_in_cache = get_secrets_from_cache(secret_arns)

    if secrets_not_in_cache:
        try:
            fetched_secrets, errors = get_secrets_from_secrets_manager(secrets_not_in_cache)

            if errors:
                error_message = f"Failed to retrieve secrets: {errors}"
                raise SecretResolutionError(error_message, errors)  # noqa: TRY301

            for secret_arn, secret_value in fetched_secrets.items():
                save_secret_in_cache(secret_arn, secret_value)
                secrets[secret_arn] = secret_value
        except Exception as e:
            if bool_env("SAFE_INIT_FAIL_ON_SECRET_RESOLUTION_ERROR"):
                raise
            log_warning("Failed to resolve some secrets", exc_info=e)

    resolved_secrets = process_secrets(secret_arns, secrets)

    log_debug("Resolved secrets", secrets=resolved_secrets.keys())

    return resolved_secrets


def gather_secret_arns(
    common_secret_arn_prefix: str | None,
    extra_env_vars: Mapping[str, str | None] | None = None,
) -> dict[str, str]:
    """
    Gathers the secret ARNs from the environment variables.

    Args:
        common_secret_arn_prefix (str): The common prefix for secret ARNs.
        extra_env_vars (Mapping[str, str] | None): Additional environment variables to consider.

    Returns:
        A dictionary mapping secret names to their ARNs.
    """
    secret_arns = {}
    env_vars = os.environ.copy()
    if extra_env_vars:
        env_vars.update(extra_env_vars)  # type: ignore[arg-type]
    for env_var, secret_arn in env_vars.items():
        if not env_var.endswith(SECRET_SUFFIX):
            continue
        secret_name = env_var[: -len(SECRET_SUFFIX)]
        secret_arns[secret_name] = (
            secret_arn
            if not common_secret_arn_prefix or secret_arn.startswith(common_secret_arn_prefix)
            else f"{common_secret_arn_prefix}{secret_arn}"
        )
    return secret_arns


def get_secrets_from_cache(secret_arns: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """
    Retrieves secrets from the cache and identifies any that are missing.

    Args:
        secret_arns (Dict[str, str]): A dictionary mapping secret names to their ARNs.

    Returns:
        A tuple containing:
        - A dictionary of secrets retrieved from the cache.
        - A list of ARNs for secrets that are not in the cache.
    """
    secrets_in_cache: dict[str, str] = {}
    secrets_not_in_cache: list[str] = []

    for _, secret_arn in secret_arns.items():
        secret_value = get_secret_from_cache(_strip_json_key_prefix_if_present(secret_arn))
        if secret_value is not None:
            secrets_in_cache[secret_arn] = secret_value
        else:
            secrets_not_in_cache.append(secret_arn)

    return secrets_in_cache, secrets_not_in_cache


def get_secrets_from_secrets_manager(secret_arns: list[str]) -> tuple[dict[str, str], list[str]]:
    """
    Retrieves secrets from AWS Secrets Manager using the batch method.

    Args:
        secret_arns (List[str]): A list of secret ARNs to retrieve.

    Returns:
        A tuple containing:
        - A dictionary of successfully retrieved secrets mapped to their original ARNs with suffixes.
        - A list of ARNs for secrets that failed to retrieve.
    """
    secrets_client = get_secrets_manager_client()
    secrets = {}
    errors = []

    # Strip json-key suffixes (if present) and create a unique set of secret ARNs
    stripped_secret_arns = {_strip_json_key_prefix_if_present(arn) for arn in secret_arns}

    try:
        response = secrets_client.batch_get_secret_value(SecretIdList=list(stripped_secret_arns))

        # Process the retrieved secrets and map them back to the original ARNs with suffixes
        for secret in response.get("SecretValues", []):
            original_secret_arn = secret["ARN"]
            secret_value = secret.get("SecretString")

            # Map the secret value to all original ARNs with suffixes
            for arn in secret_arns:
                if _strip_json_key_prefix_if_present(arn) == original_secret_arn:
                    secrets[arn] = secret_value

        for error in response.get("Errors", []):
            if error["ErrorCode"] == "ResourceNotFoundException":
                log_warning("Secret not found in Secrets Manager", secret_arn=error["SecretId"])
            else:
                errors.append(f"{error['SecretId']}: {error['Message']}")
    except ClientError as e:
        log_error("Failed to retrieve secrets from Secrets Manager", exc_info=e)
        errors.extend(secret_arns)

    return secrets, errors


def process_secrets(secret_arns: dict[str, str], secrets: dict[str, str]) -> dict[str, str]:
    """
    Processes and resolves the secrets, including handling JSON secrets.

    Args:
        secret_arns (Dict[str, str]): A dictionary mapping secret names to their ARNs.
        secrets (Dict[str, str]): A dictionary of secret values.

    Returns:
        A dictionary of processed and resolved secrets.
    """
    resolved_secrets = {}

    for secret_name, secret_arn in secret_arns.items():
        try:
            if is_json_secret := JSON_SECRET_SEPARATOR in secret_arn:
                secret_json_key = secret_arn.split(JSON_SECRET_SEPARATOR, 1)[1]

            secret_value = secrets.get(secret_arn)
            if secret_value:
                if not is_json_secret:
                    resolved_secrets[secret_name] = str(secret_value)
                    continue
                secret_json = json.loads(secret_value)
                resolved_secrets[secret_name] = str(secret_json[secret_json_key])
        except Exception as e:
            if bool_env("SAFE_INIT_FAIL_ON_SECRET_RESOLUTION_ERROR"):
                raise
            log_warning("Failed to process secret", secret_arn=secret_arn, exc_info=e)

    return resolved_secrets


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


@suppress_exceptions()
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


@suppress_exceptions()
def save_secret_in_cache(secret_arn: str, secret_value: str) -> None:
    """
    Saves the secret value in the cache.

    Args:
        secret_arn (str): The ARN of the secret to save.
        secret_value (str): The value of the secret to save.
    """
    stripped_secret_arn = _strip_json_key_prefix_if_present(secret_arn)
    if not is_secret_cache_enabled():
        log_debug("Secret caching is disabled, not saving", secret_arn=stripped_secret_arn)
        return
    redis_client = get_redis_client()
    redis_client.set(
        f"{CACHE_PREFIX}{stripped_secret_arn}",
        secret_value,
        ex=CACHE_TTL,
    )
    log_debug("Secret saved in cache", secret_arn=stripped_secret_arn)


def _strip_json_key_prefix_if_present(secret_arn: str) -> str:
    """
    Strips the JSON key suffix from the secret ARN if present.

    Args:
        secret_arn (str): The secret ARN that may include a suffix.

    Returns:
        The base secret ARN without any suffix.
    """
    return secret_arn.split(JSON_SECRET_SEPARATOR, 1)[0] if JSON_SECRET_SEPARATOR in secret_arn else secret_arn
