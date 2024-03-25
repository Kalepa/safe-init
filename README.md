# Safe Init

[![PyPI version](https://badge.fury.io/py/safe-init.svg)](https://badge.fury.io/py/safe-init)
[![Documentation Status](https://readthedocs.org/projects/safe-init/badge/?version=latest)](https://safe-init.readthedocs.io/en/latest/?badge=latest)
[![Python versions](https://img.shields.io/pypi/pyversions/safe-init.svg)](https://pypi.org/project/safe-init/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Safe Init is a Python library that provides a comprehensive set of tools for initializing AWS Lambda functions safely and handling errors and exceptions gracefully. It is designed to make your Lambda functions more robust, easier to debug, and less prone to unexpected failures. With Safe Init, you can focus on writing your core Lambda function logic while the library takes care of error handling, logging, notifications, and more.

## Features

### Error Handling and Logging
- **Error Handling**: Safe Init wraps your Lambda handler with robust error handling and logging, ensuring that any unhandled exceptions are captured and logged for easy debugging.
- **Execution Time Tracing**: Traces the execution time of all function calls within the Lambda handler, helping you identify performance bottlenecks and optimize your code.

### Monitoring and Alerting
- **Sentry Integration**: Automatically captures and logs exceptions with Sentry, providing detailed error tracking and monitoring capabilities.
- **Slack Notifications**: Sends informative Slack notifications with error details, keeping your team informed about any issues in real-time.
- **Datadog Integration**: Integrates seamlessly with the Datadog Lambda wrapper for enhanced monitoring and metrics collection.

### Resilience and Reliability
- **Dead-Letter Queue (DLQ) Support**: Pushes failed events to a dead-letter queue for later processing, ensuring that no events are lost due to errors.
- **Initialization Checks**: Detects missing Sentry initialization and Lambda init phase timeouts, preventing silent failures and providing early warning signs.
- **Timeout Notifications**: Sends notifications a configurable number of seconds before the Lambda timeout occurs, giving you a heads-up to investigate and address potential issues.

### Customization and Flexibility
- **Customizable Logger**: Allows you to use a custom logger instead of the default structlog logger, providing flexibility to integrate with your existing logging setup.
- **Easy to Use**: Simply set the Lambda handler to `safe_init.handler.handler` and configure the `SAFE_INIT_HANDLER` environment variable to point to your original code handler. No further changes or decorators needed!

## Installation

Installing Safe Init is a breeze! Simply use pip to install the library:

```bash
pip install safe-init
```

And you're ready to go! Safe Init will be your trusty sidekick, watching over your Lambda functions like a vigilant superhero. 🦸‍♂️

## Usage

Using Safe Init is as easy as pie! Just follow these simple steps:

1. Set your Lambda handler/entrypoint to `safe_init.handler.handler`.
2. Set the value of the `SAFE_INIT_HANDLER` environment variable to your original code handler.
3. Sit back, relax, and let Safe Init do its magic! 🪄

Safe Init will wrap your Lambda handler and automatically handle errors, log exceptions, send notifications, and perform all the other fantastic features mentioned above.

It's important to note that Safe Init is not meant to replace error handling in your Lambda code. Instead, it serves as a safety net, catching and handling errors and exceptions that may have slipped through the cracks. So, continue writing robust error handling in your code, and let Safe Init be your trusty sidekick, ready to save the day when needed! 🦸‍♀️

## Datadog Integration

Safe Init seamlessly integrates with the Datadog Lambda wrapper, providing enhanced monitoring and metrics collection capabilities out of the box. When using Safe Init, you no longer need to manually wrap your Lambda handler with the Datadog Lambda wrapper. Safe Init takes care of this automatically, ensuring that your Lambda functions are properly instrumented and monitored by Datadog. This integration simplifies your code and reduces the chances of errors or inconsistencies in your Datadog setup.

If you're currently using the Datadog Lambda wrapper as the entry point for your Lambda function, you can easily switch to using Safe Init instead. To do this, you'll need to update your Lambda function's configuration. First, change the entry point from `datadog_lambda.handler.handler` to `safe_init.handler.handler`. This tells AWS Lambda to use Safe Init as the entry point for your function. Next, update the environment variables. Remove the `DD_LAMBDA_HANDLER` environment variable, which is used by the Datadog Lambda wrapper to specify your original Lambda handler function. Instead, add the `SAFE_INIT_HANDLER` environment variable and set its value to the name of your original Lambda handler function, such as `your_module.lambda_handler`. By making these changes, Safe Init will automatically wrap your Lambda function with its own error handling, logging, and tracing functionality, including the Datadog Lambda wrapper. If you want to disable the automatic Datadog integration provided by Safe Init, you can optionally set the `SAFE_INIT_NO_DATADOG_WRAPPER` environment variable to `'true'`. With these configuration updates, your Lambda function will now use Safe Init as the entry point, benefiting from its enhanced features while still allowing for easy integration with Datadog if desired.

## Configuration

Safe Init provides a wide range of configuration options to customize its behavior and integrate with your existing tools and workflows. Here's a detailed look at each configuration option:

- `SAFE_INIT_HANDLER` (required): The name of your original Lambda handler function (e.g., `mymodule.lambda_handler`). This is where the magic happens!
- `SAFE_INIT_ENV` (optional): The environment name (e.g., `prod`, `staging`). Defaults to `'unknown'`. Use this to keep track of which environment your Lambda is running in.
- `SAFE_INIT_DLQ` (optional): The URL of the dead-letter queue to use for failed events. If specified, Safe Init will push failed events to this queue for later processing, ensuring that no event is left behind!
- `SAFE_INIT_SLACK_WEBHOOK_URL` (optional): The Slack webhook URL to use for notifications. If provided, Safe Init will send informative Slack notifications with error details, keeping your team in the loop.
- `SENTRY_DSN` (optional): The Sentry DSN to use for error tracking. If set, Safe Init will capture and log exceptions with Sentry, giving you detailed insights into any issues.
- `SAFE_INIT_DEBUG` (optional): Set to `'true'` to enable debug logging. Because sometimes you just need to see what's going on under the hood!
- `SAFE_INIT_NOTIFY_SEC_BEFORE_TIMEOUT` (optional): The number of seconds before the Lambda timeout to send a notification. Defaults to 5 seconds for timeouts < 120s, and 10 seconds for timeouts >= 120s. It's like a friendly tap on the shoulder, reminding you to check on your Lambda before it times out.
- `SAFE_INIT_TRACER_HOME_PATHS` (optional): A comma-separated list of paths to mark as "home" in function call tracing. Paths containing these strings will be marked with a ⚡ emoji in Slack notifications. Because home is where the heart is, and the ⚡ emoji is just cool!
- `SAFE_INIT_IGNORE_TIMEOUTS` (optional): Set to `'true'` to disable timeout notifications. For those times when you just don't want to be bothered about timeouts.
- `SAFE_INIT_NO_SLACK_TIMEOUT_NOTIFICATIONS` (optional): Set to `'true'` to disable Slack notifications for timeouts. Sometimes, you just need a break from all the notifications.
- `SAFE_INIT_NO_DATADOG_WRAPPER` (optional): Set to `'true'` to disable Datadog integration. If you're not using Datadog, this is the option for you!
- `SAFE_INIT_AUTO_TRACE_LAMBDAS` (optional): Set to `'true'` to automatically trace all function calls in Lambda handlers. **Warning:** this can significantly increase memory usage and execution time. Use with caution!
- `SAFE_INIT_LOGGING_USE_CONSOLE_RENDERER` (optional): Set to `'true'` to use the console renderer for logs. For those times when you want your logs to look extra fancy in the console.

With these configuration options, Safe Init provides a flexible and customizable way to enhance your Lambda functions' error handling, logging, and monitoring capabilities. Mix and match the options to suit your needs, and let Safe Init be your loyal companion on your Lambda adventures! 🚀

## Advanced Usage

### Custom Logger

If you prefer to use your own logger instead of the default structlog logger, Safe Init has got you covered! Simply set the `safe_init_logger_getter` global variable to a function that returns your logger instance, and Safe Init will use it for logging.

```python
import logging
import safe_init

def my_logger_getter():
    return logging.getLogger('my_logger')

safe_init.safe_logging.safe_init_logger_getter = my_logger_getter
```

Now, Safe Init will use your custom logger for all its logging needs.

### Custom Slack Webhook URL

If you don't want to set the Slack webhook URL using an environment variable, no worries! You can set the `safe_init_slack_webhook_url` global variable to your webhook URL, and Safe Init will use it for sending Slack notifications.

```python
import safe_init

safe_init.slack.safe_init_slack_webhook_url = 'https://hooks.slack.com/services/xxx/yyy/zzz'
```

And just like that, Safe Init will start sending notifications to your custom Slack webhook. It's like having your own personal messenger pigeon! 🕊️

## Full Documentation

For more detailed information on Safe Init's features, configuration options, and advanced usage, check out the full documentation on [Read the Docs](https://safe-init.readthedocs.io/). It's chock-full of useful tips, examples, and best practices to help you get the most out of Safe Init.

## Contributing

We welcome contributions from the community! Whether you have a bug fix, a new feature, or just want to improve the documentation, we appreciate your help. To contribute, please follow these steps:

1. Fork the repository on GitHub.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them with descriptive commit messages.
4. Push your changes to your forked repository.
5. Open a pull request on the main repository, describing your changes in detail.

We'll review your pull request and work with you to get it merged. Together, we can make Safe Init even better! 💪

## License

Safe Init is licensed under the MIT License. Feel free to use, modify, and distribute the library as per the terms of the license. Just remember to give a shout-out to Safe Init in your README or documentation! 📣

## Acknowledgements

Safe Init stands on the shoulders of giants and wouldn't be possible without the amazing work of the following projects:

- [Sentry](https://sentry.io/) for their excellent error tracking and monitoring platform.
- [Datadog](https://www.datadoghq.com/) for their comprehensive monitoring and observability solutions.
- [Slack](https://slack.com/) for their intuitive and collaborative communication tools.
- [structlog](https://www.structlog.org/) for their powerful and flexible logging library.
- [Kalepa](https://www.kalepa.com) for providing me with the opportunity to develop this cool library as part of my work. Their support and encouragement have been instrumental in bringing Safe Init to life.

A big thank you to all the maintainers and contributors of these projects! 🙌
