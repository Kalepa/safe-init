import json
import os
from collections.abc import Mapping

from safe_init.error_utils import suppress_exceptions
from safe_init.safe_logging import log_error, log_warning

ADDITIONAL_ENV_VARS_FILE = os.getenv("SAFE_INIT_EXTRA_ENV_VARS_FILE", ".env.json").strip()


@suppress_exceptions(default_return_value=False)
def has_extra_env_vars() -> bool:
    """
    Determines the presence of an additional environment variables file.

    Checks if the specified environment variables file exists, is non-empty, and is readable.

    Returns:
        bool: True if the file exists, is non-empty, and readable; False otherwise.
    """
    return (
        os.path.isfile(ADDITIONAL_ENV_VARS_FILE)  # noqa: PTH113
        and os.path.getsize(ADDITIONAL_ENV_VARS_FILE) > 0  # noqa: PTH202
        and os.access(ADDITIONAL_ENV_VARS_FILE, os.R_OK)
    )


@suppress_exceptions(default_return_value={})
def load_extra_env_vars() -> Mapping[str, str | None]:
    """
    Loads additional environment variables from a JSON file.

    The file path is determined by the `SAFE_INIT_EXTRA_ENV_VARS_FILE` environment variable.
    The JSON file must contain a flat dictionary with string keys and string or null values.

    Returns:
        Mapping[str, Optional[str]]: A dictionary of environment variables.
            Returns an empty dictionary if the file cannot be loaded or contains invalid data.
    """
    try:
        with open(ADDITIONAL_ENV_VARS_FILE) as f:
            data = json.load(f)
    except Exception as e:
        log_error(
            "Failed to load the extra environment variables file. Not loading extra env vars.",
            file=ADDITIONAL_ENV_VARS_FILE,
            exc_info=e,
        )
        return {}

    if not isinstance(data, dict):
        log_error(
            "The extra environment variables file must contain a JSON object. Not loading extra env vars.",
            file_content=data,
        )
        return {}

    processed_data = {}
    for key, value in data.items():
        if not isinstance(key, str):
            log_error(
                "Keys in the extra environment variables file must be strings. Skipping key.",
                key=key,
                key_type=type(key),
                value=value,
            )
            continue

        if not isinstance(value, str | type(None)):
            value_type = type(value)
            orig_value = value

            try:
                value = str(value)  # noqa: PLW2901
            except Exception as e:
                log_error(
                    (
                        "Values in the extra environment variables file should be strings or null. Converting to string"
                        " failed, skipping key."
                    ),
                    key=key,
                    value=orig_value,
                    value_type=value_type,
                    exc_info=e,
                )
                continue

            log_warning(
                "Values in the extra environment variables file should be strings or null. Converting to string.",
                key=key,
                value=orig_value,
                value_type=value_type,
                converted_value=value,
            )

        processed_data[key] = value

    return processed_data
