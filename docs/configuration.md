# Configuration

Safe Init provides a flexible and extensive configuration system primarily through environment variables, allowing for easy integration and customization in various environments, especially when working with AWS Lambda functions. Below is a comprehensive guide to configuring Safe Init to fit your needs.

## Configuration Options Overview

| Environment Variable                      | Description                                                                                   | Default Value |
|-------------------------------------------|-----------------------------------------------------------------------------------------------|---------------|
| `SAFE_INIT_HANDLER`                       | The name of your original Lambda handler function.                                            | None (required) |
| `SAFE_INIT_ENV`                           | The environment name where the Lambda function is running (e.g., `prod`, `dev`).              | `unknown` |
| `SAFE_INIT_DLQ`                           | The URL of the dead-letter queue to use for failed events.                                    | None |
| `SAFE_INIT_SLACK_WEBHOOK_URL`             | The Slack webhook URL for sending notifications.                                              | None |
| `SENTRY_DSN`                              | The Sentry DSN for error tracking and logging.                                                | None |
| `SAFE_INIT_DEBUG`                         | Enable debug logging.                                                                         | False |
| `SAFE_INIT_NOTIFY_SEC_BEFORE_TIMEOUT`     | Seconds before the Lambda timeout to send a notification.                                     | 5 (for <120s timeouts), 10 (for >=120s) |
| `SAFE_INIT_TRACER_HOME_PATHS`             | Comma-separated list of paths to mark as "home" in function call tracing.                     | None |
| `SAFE_INIT_IGNORE_TIMEOUTS`               | Disable timeout notifications.                                                                | False |
| `SAFE_INIT_NO_SLACK_TIMEOUT_NOTIFICATIONS`| Disable Slack notifications for timeouts.                                                     | False |
| `SAFE_INIT_NO_DATADOG_WRAPPER`            | Disable automatic Datadog integration.                                                        | False |
| `SAFE_INIT_AUTO_TRACE_LAMBDAS`            | Automatically trace all function calls in Lambda handlers.                                    | False |
| `SAFE_INIT_LOGGING_USE_CONSOLE_RENDERER`  | Use the console renderer for logs.                                                            | False |

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

### `SAFE_INIT_NO_DATADOG_WRAPPER`
Setting this variable to `true` disables the automatic wrapping of your Lambda function with the Datadog Lambda wrapper. This is useful if you are not using Datadog for monitoring or if you wish to manually configure the Datadog integration. Disabling the automatic wrapper gives you full control over how and when your functions are instrumented with Datadog.

### `SAFE_INIT_AUTO_TRACE_LAMBDAS`
When set to `true`, this option instructs Safe Init to automatically trace all function calls within your Lambda handler. This can significantly aid in debugging by providing insights into the execution flow and performance bottlenecks. However, be aware that enabling this feature can increase both the memory footprint and the execution time of your Lambda functions due to the overhead of tracing.

### `SAFE_INIT_LOGGING_USE_CONSOLE_RENDERER`
By default, Safe Init uses a JSON renderer for logs to facilitate log ingestion and parsing in various log management systems. However, setting this variable to `true` switches the logging output to a more human-readable console format. This can be particularly useful during local development and testing, where readability of logs takes precedence over machine parsing.

## Advanced Configuration

### Combining Environment Variables for Fine-Grained Control
Many of Safe Init's features can be fine-tuned by combining multiple environment variables. For instance, you might set a specific pre-timeout notification value (`SAFE_INIT_NOTIFY_SEC_BEFORE_TIMEOUT=15`) while also suppressing Slack timeout notifications (`SAFE_INIT_NO_SLACK_TIMEOUT_NOTIFICATIONS=true`) to focus on specific aspects of your Lambda's behavior during development phases.

### Dynamic Configuration in Code
While Safe Init is designed to be configured via environment variables, certain scenarios might require dynamic configuration within your Lambda code. For example, you might need to adjust the Slack webhook URL based on the function's input or execution context. In such cases, Safe Init offers a limited set of global variables that can be programmatically set within your Lambda handler or initialization code. However, this approach should be used sparingly and with caution, as it can make your configuration less transparent and harder to manage.
