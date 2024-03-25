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

## Customization and Flexibility

Safe Init is designed to be flexible and customizable, allowing you to tailor its behavior to fit your specific needs.

### Customizable Logger

Safe Init uses `structlog` for structured logging but allows you to integrate your custom logger if you prefer.

**Configuration Options:**

- Custom Logger Integration: Implement the `safe_init_logger_getter` function to return your custom logger instance. This function is used by Safe Init to log messages, enabling you to maintain consistency with your existing logging setup.
