# Usage

Using Safe Init in your AWS Lambda functions, or similar environments, enhances error handling, logging, notifications, and monitoring with minimal setup. This guide covers integrating Safe Init into your projects, setting environment variables, and utilizing its features effectively.

## Prerequisites

Before integrating Safe Init, ensure you have:

- Installed Safe Init via pip (`pip install safe-init`)
- Basic knowledge of AWS Lambda and environment variables

## Setting up Safe Init

To set up Safe Init, you need to modify your Lambda function's handler and configure a few environment variables. Here's how to do it step by step:

### Step 1: Modify Lambda Handler

In the AWS Lambda console or your `serverless.yml` (if using the Serverless framework), change the Lambda function's handler to point to Safe Init's handler:

```plaintext
safe_init.handler.handler
```

This setting tells AWS Lambda to use Safe Init as the entry point for your function.

### Step 2: Configure `SAFE_INIT_HANDLER`

Set the `SAFE_INIT_HANDLER` environment variable to the path of your original handler. For example, if your handler was `my_module.my_handler`, set `SAFE_INIT_HANDLER` to `my_module.my_handler`.

### Step 3: Additional Configuration

Optionally, configure Safe Init's behavior through environment variables to utilize features like Sentry integration, Slack notifications, dead-letter queue support, and more. Here are some of the key variables:

- `SENTRY_DSN`: Your Sentry project's DSN for exception tracking.
- `SAFE_INIT_SLACK_WEBHOOK_URL`: The Slack webhook URL for sending error notifications.
- `SAFE_INIT_DLQ`: The URL of the dead-letter queue for failed events.

## Advanced Configuration

Beyond basic setup, Safe Init offers advanced configurations for deeper customization and integration:

### Custom Logger

By default, Safe Init uses structlog for logging. To use a custom logger:

1. Import your logger and Safe Init in your Lambda code.
2. Assign your logger to `safe_init.safe_logging.safe_init_logger_getter`.

Example:

```python
import logging
import safe_init

def custom_logger():
    return logging.getLogger("my_custom_logger")

safe_init.safe_logging.safe_init_logger_getter = custom_logger
```

### Execution Time Tracing

Enable execution time tracing to identify performance bottlenecks:

1. Set the `SAFE_INIT_AUTO_TRACE_LAMBDAS` environment variable to `true`.
2. Optionally, use `SAFE_INIT_TRACER_HOME_PATHS` to highlight specific paths in traces.

## Using with Other AWS Services and FaaS

Safe Init can also be used with AWS Batch, Google Cloud Functions, and other FaaS platforms that allow custom Python handlers.

### AWS Batch

For AWS Batch jobs, wrap your job entry point with Safe Init's handler following similar steps as for AWS Lambda. Ensure to set environment variables in your job definition.

### Google Cloud Functions

In Google Cloud Functions, set the entry point to Safe Init's handler and configure the `SAFE_INIT_HANDLER` environment variable to point to your function. Use Google Cloud's environment variable configuration to set additional Safe Init options.

## Best Practices

- **Error Handling**: Continue implementing error handling in your functions. Safe Init complements, but does not replace, proper error management in your code.
- **Environment Specific Configuration**: Use different sets of environment variables for different deployment stages (e.g., development, staging, production) to separate monitoring and notifications.
- **Performance Monitoring**: Regularly review execution time traces and logs to optimize your function's performance.

By following these steps and recommendations, you can significantly enhance the reliability, maintainability, and observability of your serverless applications with Safe Init.
