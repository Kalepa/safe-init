# Configuration

Safe Init provides a flexible and extensive configuration system primarily through environment variables, allowing for easy integration and customization in various environments, especially when working with AWS Lambda functions. Below is a comprehensive guide to configuring Safe Init to fit your needs.

## Configuration Options Overview

| Environment Variable                        | Description                                                                                   | Default Value                           |
|---------------------------------------------|-----------------------------------------------------------------------------------------------|-----------------------------------------|
| `SAFE_INIT_HANDLER`                         | The name of your original Lambda handler function.                                            | None (required)                         |
| `SAFE_INIT_ENV`                             | The environment name where the Lambda function is running (e.g., `prod`, `dev`).              | `unknown`                               |
| `SAFE_INIT_DLQ`                             | The URL of the dead-letter queue to use for failed events.                                    | None                                    |
| `SAFE_INIT_SLACK_WEBHOOK_URL`               | The Slack webhook URL for sending notifications.                                              | None                                    |
| `SENTRY_DSN`                                | The Sentry DSN for error tracking and logging.                                                | None                                    |
| `SAFE_INIT_DEBUG`                           | Enable debug logging.                                                                         | False                                   |
| `SAFE_INIT_NOTIFY_SEC_BEFORE_TIMEOUT`       | Seconds before the Lambda timeout to send a notification.                                     | 5 (for <120s timeouts), 10 (for >=120s) |
| `SAFE_INIT_TRACER_HOME_PATHS`               | Comma-separated list of paths to mark as "home" in function call tracing.                     | None                                    |
| `SAFE_INIT_IGNORE_TIMEOUTS`                 | Disable timeout notifications.                                                                | False                                   |
| `SAFE_INIT_NO_SLACK_TIMEOUT_NOTIFICATIONS`  | Disable Slack notifications for timeouts.                                                     | False                                   |
| `SAFE_INIT_ALWAYS_NOTIFY_SLACK`             | Always send error notifications to Slack, even if successfully sent to Sentry.                | False                                   |
| `SAFE_INIT_NO_DATADOG_WRAPPER`              | Disable automatic Datadog integration.                                                        | False                                   |
| `SAFE_INIT_AUTO_TRACE_LAMBDAS`              | Automatically trace all function calls in Lambda handlers.                                    | False                                   |
| `SAFE_INIT_LOGGING_USE_CONSOLE_RENDERER`    | Use the console renderer for logs.                                                            | False                                   |
| `SAFE_INIT_RESOLVE_SECRETS`                 | Resolve AWS Secrets Manager secrets in environment variables.                                 | False                                   |
| `SAFE_INIT_SECRET_SUFFIX`                   | The suffix to use for resolving AWS Secrets Manager secrets in environment variables.         | `_SECRET_ARN`                           |
| `SAFE_INIT_SECRET_ARN_PREFIX`               | The prefix to use for AWS Secrets Manager secret ARNs in environment variables.               | None                                    |
| `SAFE_INIT_CACHE_SECRETS`                   | Cache resolved secrets in Redis.                                                              | False                                   |
| `SAFE_INIT_SECRET_CACHE_REDIS_HOST`         | Hostname of the Redis server used for caching secrets. Required if secret caching is enabled. | None                                    |
| `SAFE_INIT_SECRET_CACHE_REDIS_PORT`         | Port of the Redis server used for caching secrets. Required if secret caching is enabled.     | None                                    |
| `SAFE_INIT_SECRET_CACHE_REDIS_DB`           | Database number of the Redis server used for caching secrets.                                 | 0                                       |
| `SAFE_INIT_SECRET_CACHE_REDIS_USERNAME`     | Username for the Redis server used for caching secrets.                                       | None                                    |
| `SAFE_INIT_SECRET_CACHE_REDIS_PASSWORD`     | Password for the Redis server used for caching secrets.                                       | None                                    |
| `SAFE_INIT_SECRET_CACHE_TTL`                | TTL for cached secrets in seconds.                                                            | 1800 (30 minutes)                       |
| `SAFE_INIT_SECRET_CACHE_PREFIX`             | Prefix for cached secrets in Redis.                                                           | `safe-init-secret::`                    |
| `SAFE_INIT_FAIL_ON_SECRET_RESOLUTION_ERROR` | Fail the Lambda initialization if an error occurs during secret resolution.                   | False                                   |
| `SAFE_INIT_EXTRA_ENV_VARS_FILE`             | Path to a file containing additional environment variables to load.                           | `.env.json`                             |

## Detailed Configuration Options

### `SAFE_INIT_HANDLER`
This environment variable is critical for Safe Init's operation. It should be set to the fully qualified name of your original Lambda handler function, including the module name. For example, if your handler function is named `lambda_handler` and is located in a file named `my_module.py`, you would set `SAFE_INIT_HANDLER` to `my_module.lambda_handler`. This setting tells Safe Init which function to wrap with its error handling and logging capabilities.

### `SAFE_INIT_ENV`
Setting this variable allows you to specify the environment in which your Lambda function is running, such as `production`, `development`, or `staging`. This is particularly useful for filtering and categorizing logs and error reports in external monitoring and logging tools like Sentry or Datadog.

### `SAFE_INIT_DLQ`
If specified, Safe Init will push failed events to the dead-letter queue (DLQ) provided in this URL. This ensures that no event is lost due to processing errors. The DLQ can be an Amazon SQS queue, which is useful for later analysis or reprocessing of failed events.

### `SAFE_INIT_SLACK_WEBHOOK_URL`
This variable should contain the Slack webhook URL to which Safe Init will send notifications about errors and other critical issues. Setting up a Slack webhook allows you to receive real-time alerts directly in your chosen Slack channel, keeping your team informed about the health and status of your Lambda functions.

### `SENTRY_DSN`
By providing a Sentry DSN, you enable Safe Init to automatically capture and log exceptions with Sentry. This integration provides detailed error tracking and monitoring capabilities, making it easier to diagnose and fix issues in your Lambda functions.

### `SAFE_INIT_DEBUG`
When set to `true`, this enables debug logging, providing more detailed logs that can help with troubleshooting and development. Debug logs include information about the internal operations of Safe Init, such as function wrapping and error handling processes.

### `SAFE_INIT_NOTIFY_SEC_BEFORE_TIMEOUT`
This option allows you to configure the number of seconds before a Lambda's configured timeout at which Safe Init will send a notification. This is useful for catching and investigating functions that are at risk of timing out before they actually do, allowing for preemptive action.

### `SAFE_INIT_TRACER_HOME_PATHS`
This comma-separated list of paths helps Safe Init determine which parts of your codebase to consider as "home" when performing function call tracing. Functions located in files that contain any of these paths in their file paths will be marked with a ⚡ emoji in Slack notifications, highlighting critical paths in your application.

### `SAFE_INIT_IGNORE_TIMEOUTS`
Setting this to `true` disables the timeout notification feature. This can be useful in environments where function timeouts are expected or handled differently and you do not want Safe Init to send additional notifications.

### `SAFE_INIT_NO_SLACK_TIMEOUT_NOTIFICATIONS`
When set to `true`, this prevents Safe Init from sending Slack notifications specifically for Lambda execution timeouts. This can be useful if you wish to limit the volume of Slack notifications or handle timeout alerts through another mechanism.

### `SAFE_INIT_ALWAYS_NOTIFY_SLACK`
By default, Safe Init sends error notifications to Slack only if it fails to send the error to Sentry. However, setting this variable to `true` forces Safe Init to always send error notifications to Slack, regardless of whether the error was successfully reported to Sentry.

### `SAFE_INIT_NO_DATADOG_WRAPPER`
Setting this variable to `true` disables the automatic wrapping of your Lambda function with the Datadog Lambda wrapper. This is useful if you are not using Datadog for monitoring or if you wish to manually configure the Datadog integration. Disabling the automatic wrapper gives you full control over how and when your functions are instrumented with Datadog.

### `SAFE_INIT_AUTO_TRACE_LAMBDAS`
When set to `true`, this option instructs Safe Init to automatically trace all function calls within your Lambda handler. This can significantly aid in debugging by providing insights into the execution flow and performance bottlenecks. However, be aware that enabling this feature can increase both the memory footprint and the execution time of your Lambda functions due to the overhead of tracing.

### `SAFE_INIT_LOGGING_USE_CONSOLE_RENDERER`
By default, Safe Init uses a JSON renderer for logs to facilitate log ingestion and parsing in various log management systems. However, setting this variable to `true` switches the logging output to a more human-readable console format. This can be particularly useful during local development and testing, where readability of logs takes precedence over machine parsing.

### `SAFE_INIT_RESOLVE_SECRETS`
When set to `true`, Safe Init will resolve AWS Secrets Manager secrets in environment variables. This feature allows you to securely store and retrieve sensitive information like API keys, database credentials, and other secrets within your Lambda functions. Secrets are resolved by looking for environment variables with names ending in a specified suffix (see `SAFE_INIT_SECRET_SUFFIX`) and creating new ones with the actual secret values.

### `SAFE_INIT_SECRET_SUFFIX`
This variable specifies the suffix used to identify environment variables containing AWS Secrets Manager secret ARNs. By default, Safe Init looks for environment variables ending with `_SECRET_ARN` to resolve secrets. You can customize this suffix to match your naming convention for secret ARNs. For compatibility purposes, `SAVE_INIT_SECRET_ARN_SUFFIX` is also supported as an alias for this variable.

### `SAFE_INIT_SECRET_ARN_PREFIX`
If specified, the value of this variable is appended to the beginning of AWS Secrets Manager secret ARNs found in environment variables. This can be useful for reducing redundancy in your environment variables by specifying a common prefix for all secret ARNs. For example, if your secret ARNs typically start with `arn:aws:secretsmanager:`, you can set `SAFE_INIT_SECRET_ARN_PREFIX` to `arn:aws:secretsmanager:` to avoid repeating this prefix in every secret ARN.

### `SAFE_INIT_CACHE_SECRETS`
Setting this variable to `true` enables Safe Init to cache resolved secrets in Redis. Caching secrets can help reduce the number of calls to AWS Secrets Manager, improving performance and reducing costs. If you enable secret caching, you must provide the necessary Redis connection details (host, port, database, and password) using the corresponding environment variables.

- `SAFE_INIT_SECRET_CACHE_REDIS_HOST`: The hostname of the Redis server used for caching secrets (required).
- `SAFE_INIT_SECRET_CACHE_REDIS_PORT`: The port of the Redis server used for caching secrets (required).
- `SAFE_INIT_SECRET_CACHE_REDIS_DB`: The database number of the Redis server used for caching secrets.
- `SAFE_INIT_SECRET_CACHE_REDIS_USERNAME`: The username for the Redis server used for caching secrets.
- `SAFE_INIT_SECRET_CACHE_REDIS_PASSWORD`: The password for the Redis server used for caching secrets.

### `SAFE_INIT_SECRET_CACHE_TTL`
This variable specifies the time-to-live (TTL) for cached secrets in seconds. After this duration, cached secrets will expire and be re-fetched from AWS Secrets Manager. The default TTL is 30 minutes (1800 seconds), but you can adjust this value based on your application's requirements.

### `SAFE_INIT_SECRET_CACHE_PREFIX`
This prefix is used to identify cached secrets in Redis. By default, Safe Init uses `safe-init-secret::` as the prefix for cached secrets. You can customize this prefix to avoid conflicts with other keys in your Redis instance.

### `SAFE_INIT_FAIL_ON_SECRET_RESOLUTION_ERROR`
When set to `true`, this option causes the Lambda initialization to fail if an error occurs during secret resolution. This can be useful for ensuring that your Lambda functions do not start with unresolved secrets, which could lead to runtime errors or security vulnerabilities.

### `SAFE_INIT_EXTRA_ENV_VARS_FILE`
This variable specifies the path to a file containing additional environment variables to load into the Lambda execution environment. The file should be in JSON format, with each key-value pair representing an environment variable. This feature allows you to inject custom configuration settings or sensitive data into your Lambda functions without hardcoding them in your code or deployment scripts, and to work around the insane 4KB limit on environment variable size in AWS Lambda.

## Advanced Configuration

### Combining Environment Variables for Fine-Grained Control
Many of Safe Init's features can be fine-tuned by combining multiple environment variables. For instance, you might set a specific pre-timeout notification value (`SAFE_INIT_NOTIFY_SEC_BEFORE_TIMEOUT=15`) while also suppressing Slack timeout notifications (`SAFE_INIT_NO_SLACK_TIMEOUT_NOTIFICATIONS=true`) to focus on specific aspects of your Lambda's behavior during development phases.

### Dynamic Configuration in Code
While Safe Init is designed to be configured via environment variables, certain scenarios might require dynamic configuration within your Lambda code. For example, you might need to adjust the Slack webhook URL based on the function's input or execution context. In such cases, Safe Init offers a limited set of global variables that can be programmatically set within your Lambda handler or initialization code. However, this approach should be used sparingly and with caution, as it can make your configuration less transparent and harder to manage.
