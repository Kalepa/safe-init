# Getting Started with Safe Init

Welcome to Safe Init, a powerful Python library designed to enhance the resilience and maintainability of your AWS Lambda functions and other FaaS environments. This guide will walk you through installing Safe Init and setting it up for your project.

## Installation

Installing Safe Init is straightforward and requires only a single command. Make sure you have Python 3.6 or later installed on your system. To install Safe Init, open your terminal and run:

```bash
pip install safe-init
```

This command installs the latest version of Safe Init from PyPI and makes it available in your Python environment.

## Basic Setup

To get started with Safe Init, you need to configure your Lambda function to use Safe Init as its handler. Follow the steps below to set up Safe Init with your Lambda function.

### Step 1: Set Lambda Handler

In your AWS Lambda configuration, set the handler to:

```
safe_init.handler.handler
```

This setting tells AWS Lambda to pass control to the Safe Init handler, which then initializes and wraps your actual handler for enhanced error handling and logging.

### Step 2: Configure Your Original Handler

Safe Init needs to know the location of your original Lambda function handler. This is done by setting the `SAFE_INIT_HANDLER` environment variable in your Lambda configuration. The value of this variable should be the Python module path to your handler function, similar to how you would normally configure a Lambda function handler.

For example, if your handler function is named `lambda_handler` and is located in a file named `app.py`, set `SAFE_INIT_HANDLER` to:

```
app.lambda_handler
```

### Step 3: Additional Configuration (Optional)

Safe Init offers various configuration options through environment variables to customize its behavior according to your needs. For example, to integrate with Sentry for error tracking, set the `SENTRY_DSN` environment variable to your Sentry DSN value. Check the [Configuration](configuration.md) section for a detailed list of all available options.

## Next Steps

With Safe Init installed and set up, your Lambda functions are now more robust against errors and equipped with better logging and monitoring capabilities. To further customize Safe Init and utilize its full potential, proceed to the [Usage](usage.md) and [Configuration](configuration.md) sections of the documentation.

Explore the [Features](features.md) section to learn more about what Safe Init offers, such as integration with Sentry, Slack notifications, dead-letter queue support, and much more.

If you encounter any issues or have questions, the [Troubleshooting](troubleshooting.md) section is a good place to start.
