# Welcome to Safe Init

Safe Init is a Python library designed to enhance the resilience, reliability, and maintainability of AWS Lambda functions and other serverless architectures. By providing advanced error handling, logging, and integration capabilities, Safe Init ensures that your serverless applications are not only robust against errors and exceptions but also easy to monitor and debug.

## Key Features

- **Comprehensive Error Handling**: Wraps your Lambda handlers to catch unhandled exceptions, making debugging easier.
- **Execution Time Tracing**: Identifies performance bottlenecks by tracing the execution time of your function calls.
- **Integrated Monitoring and Alerting**: Seamlessly integrates with Sentry for error tracking, Slack for real-time notifications, and Datadog for monitoring and metrics collection.
- **Dead-Letter Queue Support**: Ensures no events are lost due to errors by pushing failed events to a specified dead-letter queue.
- **Flexible and Easy to Use**: With minimal setup required, you can start using Safe Init by simply setting your Lambda handler and configuring a few environment variables.

## Quick Start

1. **Install Safe Init**:

```bash
pip install safe-init
```

2. **Configure Your Lambda Function**:

Set your Lambda function's handler to `safe_init.handler.handler` in the AWS Lambda console or your serverless framework configuration.

3. **Set Environment Variables**:

Set the `SAFE_INIT_HANDLER` environment variable to point to your original handler, e.g., `my_module.my_handler`.

## Explore Further

- [Getting Started](getting_started.md): Learn how to install and configure Safe Init for your project.
- [Features](features.md): Dive deeper into the features and capabilities of Safe Init.
- [Configuration](configuration.md): Understand all the configuration options available.
- [Advanced Usage](advanced_usage.md): Explore advanced use cases and customization options.

Safe Init is open-source and community-driven. Contributions, feedback, and questions are welcome!

## Quick Links

- [GitHub Repository](https://github.com/Kalepa/safe-init): View the source code, contribute, and report issues.
- [Documentation](https://safe-init.readthedocs.io): Read the full documentation and guides.
- [PyPI Package](https://pypi.org/project/safe-init): Download the latest version from PyPI.
