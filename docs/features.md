# Features

Safe Init is designed to enhance the resilience, monitoring, and error handling capabilities of your AWS Lambda functions and other serverless environments. This document provides an in-depth look at its features, configuration options, and how they contribute to making your serverless applications more robust and maintainable.

## Error Handling and Logging

Safe Init automates and enhances the error handling and logging within your serverless applications, ensuring that unhandled exceptions are captured, logged, and notified appropriately.

### Robust Error Handling

Safe Init wraps your Lambda handler function, providing a safety net for uncaught exceptions. This feature ensures that all exceptions are captured, regardless of where they occur within your Lambda function. By capturing these exceptions, Safe Init prevents your application from failing silently, enabling quicker debugging and resolution.

**Configuration Options:**

- `SAFE_INIT_HANDLER`: Specify the entry point of your Lambda function. Safe Init uses this information to correctly wrap your function for error handling.
- `SAFE_INIT_DEBUG`: Enables debug logging, offering more detailed logs that can be crucial for diagnosing issues. This setting is particularly useful during development and testing phases.

### Execution Time Tracing

Understanding the performance characteristics of your serverless functions is crucial for optimization and cost management. Safe Init includes execution time tracing, which measures and logs the execution time of your function and its subcomponents. This feature is invaluable for identifying performance bottlenecks and optimizing your application.

**Configuration Options:**

- `SAFE_INIT_AUTO_TRACE_LAMBDAS`: When set to `true`, Safe Init automatically traces all function calls within your Lambda handler. Note that this can increase memory usage and execution time, so use it judiciously.

## Monitoring and Alerting

Safe Init integrates with popular monitoring and alerting tools like Sentry, Slack, and Datadog, providing you with real-time notifications and detailed insights into your application's health and performance.

### Sentry Integration

Sentry is an open-source error tracking tool that helps developers monitor and fix crashes in real-time. Safe Init's integration with Sentry ensures that all exceptions, along with useful context, are automatically reported to your Sentry project.

**Configuration Options:**

- `SENTRY_DSN`: The Data Source Name (DSN) provided by Sentry, which Safe Init uses to report exceptions. This is required for Sentry integration.
- `SAFE_INIT_ENV`: Specifies the environment name (e.g., `prod`, `staging`) which is reported to Sentry, helping you distinguish between errors occurring in different environments.

### Slack Notifications

Stay informed of your application's health with real-time Slack notifications. Safe Init can send detailed error reports and alerts directly to a specified Slack channel, ensuring that your team is always aware of critical issues.

**Configuration Options:**

- `SAFE_INIT_SLACK_WEBHOOK_URL`: The webhook URL for your Slack channel. Safe Init uses this URL to send notifications about exceptions and other important alerts.

### Datadog Integration

Datadog offers comprehensive monitoring solutions for cloud-scale applications. Safe Init's seamless integration with Datadog's Lambda wrapper allows you to collect metrics, traces, and logs without any additional setup.

**Configuration Options:**

- `SAFE_INIT_NO_DATADOG_WRAPPER`: Set to `true` to disable the automatic wrapping of your Lambda handler with the Datadog Lambda wrapper. This is useful if you wish to use Datadog's features without Safe Init's automatic integration, or not to use Datadog at all.

## Resilience and Reliability

Safe Init enhances the resilience of your serverless applications with features like dead-letter queue support and timeout notifications, ensuring that your applications can handle failures gracefully.

### Dead-Letter Queue (DLQ) Support

Safe Init can automatically push failed events to a specified dead-letter queue (DLQ), allowing you to capture and reprocess events that could not be handled successfully due to errors.

**Configuration Options:**

- `SAFE_INIT_DLQ`: The URL of the dead-letter queue where Safe Init should push failed events. This ensures that no event is lost due to processing errors.

### Timeout Notifications

Receive proactive notifications before your Lambda function times out. This feature gives you the opportunity to investigate and address potential issues before they impact your application's availability.

**Configuration Options:**

- `SAFE_INIT_NOTIFY_SEC_BEFORE_TIMEOUT`: Specifies the number of seconds before a Lambda timeout occurs when Safe Init should send a notification. This helps you become aware of and address timeout-related issues proactively.

### JSON Serialization Checks

Safe Init automatically checks if your Lambda function's return value can be properly serialized to JSON. If the result contains non-serializable objects (like custom classes, UUIDs, etc.), Safe Init will report the issue to Sentry while allowing execution to continue normally. This gives you early notification of serialization issues that would otherwise result in failed Lambda executions.

**Configuration Options:**

- `SAFE_INIT_NO_CHECK_JSON_SERIALIZATION`: Set to `true` to disable the automatic JSON serialization check. By default, Safe Init will check if the Lambda result is JSON serializable and send an exception to Sentry if not.

### AWS Secrets Manager Integration

Safe Init integrates with AWS Secrets Manager, allowing you to securely store and retrieve sensitive information like API keys, database credentials, and other secrets. This feature ensures that your secrets are managed securely and are easily accessible within your Lambda functions.

**Configuration Options:**

- `SAFE_INIT_RESOLVE_SECRETS`: Set to `true` to resolve AWS Secrets Manager secrets in environment variables. Safe Init will automatically resolve secrets in environment variables with names ending with a configured suffix and save them in environment variables with the original name minus the suffix.
- `SAFE_INIT_SECRET_SUFFIX`: The suffix to use for resolving AWS Secrets Manager secrets in environment variables. Defaults to `_SECRET_ARN`. Use this to specify the suffix that marks environment variables as containing secret ARNs.
- `SAFE_INIT_SECRET_ARN_PREFIX`: The prefix to use for AWS Secrets Manager secret ARNs in environment variables. Use this to save some space in your environment variables by specifying a prefix with which all secret ARNs start.
- `SAFE_INIT_CACHE_SECRETS`: Set to `true` to cache resolved secrets in Redis. Safe Init will cache resolved secrets in Redis to reduce the number of calls to AWS Secrets Manager.
- `SAFE_INIT_SECRET_CACHE_REDIS_HOST`, `SAFE_INIT_SECRET_CACHE_REDIS_PORT`, `SAFE_INIT_SECRET_CACHE_REDIS_DB`, `SAFE_INIT_SECRET_CACHE_REDIS_USERNAME`, `SAFE_INIT_SECRET_CACHE_REDIS_PASSWORD` (host&port required if secret caching enabled): Redis connection details for caching resolved secrets. Use these environment variables to specify the Redis host, port, database, and password for caching resolved secrets.
- `SAFE_INIT_SECRET_CACHE_TTL`: TTL for cached secrets in seconds. Defaults to 1800 seconds (30 minutes). Use this to specify how long resolved secrets should be cached in Redis.
- `SAFE_INIT_SECRET_CACHE_PREFIX`: Prefix for cached secrets in Redis. Defaults to `safe-init-secret::`. Use this to specify the prefix for keys used to store cached secrets in Redis.
- `SAFE_INIT_FAIL_ON_SECRET_RESOLUTION_ERROR` (optional): Set to `true` to fail the Lambda initialization if an error occurs during secret resolution. Safe Init will raise an exception if an error occurs during secret resolution, preventing the Lambda function from starting.

**Example:**

Let's assume that you have a secret stored in AWS Secrets Manager with the name `my_secret` and the following ARN: `arn:aws:secretsmanager:us-east-1:123456789012:secret:my_secret-AbCdEf`.

In your Lambda function, set the following environment variables:

```bash
SAFE_INIT_RESOLVE_SECRETS=true
MY_SECRET_SECRET_ARN=arn:aws:secretsmanager:us-east-1:123456789012:secret:my_secret-AbCdEf
```

When your Lambda function starts, Safe Init will automatically resolve the secret stored in AWS Secrets Manager and save it in an environment variable named `MY_SECRET`.

**Advanced usage: JSON secrets**

If your secret is a JSON object, you can specify the key to extract from it by appending it to the ARN with a `~` separator. For example, if your secret is a JSON object like this:

```json
{
  "username": "admin",
  "password": "s3cr3t"
}
```

You can specify the key to extract like this:

```bash
USERNAME_SECRET_ARN=arn:aws:secretsmanager:us-east-1:123456789012:secret:my_secret-AbCdEf~username
PASSWORD_SECRET_ARN=arn:aws:secretsmanager:us-east-1:123456789012:secret:my_secret-AbCdEf~password
```

In this case, Safe Init will resolve the secret and save the extracted values in the `USERNAME` and `PASSWORD` environment variables.

### Unlimited Environment Variables

Safe Init allows you to define an unlimited number of environment variables for your Lambda functions, enabling you to manage and access configuration values more effectively. Just encode some or all of your environment variables as a JSON object, save in a file deployed alongside your Lambda function code (default `.env.json`), and Safe Init will automatically load them into your Lambda function's environment.

**Configuration Options:**

- `SAFE_INIT_EXTRA_ENV_VARS_FILE` (default: `.env.json`): The file path where additional environment variables are stored. Safe Init will load these variables into your Lambda function's environment.

## Customization and Flexibility

Safe Init is designed to be flexible and customizable, allowing you to tailor its behavior to fit your specific needs.

### Customizable Logger

Safe Init uses `structlog` for structured logging but allows you to integrate your custom logger if you prefer.

**Configuration Options:**

- Custom Logger Integration: Implement the `safe_init_logger_getter` function to return your custom logger instance. This function is used by Safe Init to log messages, enabling you to maintain consistency with your existing logging setup.
