# Advanced Usage

This section dives deep into the more advanced capabilities of Safe Init, providing seasoned Python developers with the insights needed to leverage this tool to its fullest. Whether you're looking to customize logging, monitor function execution more closely, or integrate Safe Init seamlessly into complex environments, this guide has you covered.

## Custom Logger Configuration

While Safe Init uses `structlog` for logging by default, it's flexible enough to accommodate your custom logging setup. Here’s how you can integrate a custom `structlog` logger:

### Example: Custom `structlog` Logger

```python
import structlog
from structlog.stdlib import LoggerFactory

# Configure structlog to use standard library's logging module
structlog.configure(logger_factory=LoggerFactory())

# Define your custom logger configuration
structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.render_to_log_kwargs,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Custom function to retrieve the configured logger
def my_logger_getter():
    return structlog.get_logger('my_custom_logger')

# Assign your custom logger to Safe Init
import safe_init
safe_init.safe_logging.safe_init_logger_getter = my_logger_getter
```

This example demonstrates how to set up a `structlog` logger with custom formatting and assign it to Safe Init, ensuring all internal logging respects your preferred configuration.

## Custom Slack Webhook URL

While the `SAFE_INIT_SLACK_WEBHOOK_URL` environment variable is the standard way to set your Slack webhook URL, Safe Init allows you to programmatically set this URL:

### Example: Setting Slack Webhook URL Programmatically

```python
import safe_init

# Manually specify the Slack webhook URL
safe_init.slack.safe_init_slack_webhook_url = 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'
```

This approach is particularly useful in scenarios where environment variables might not be the best option for configuration management.

## Monkey Patching Slack Notifications

For cases where you need to modify the behavior of Slack notifications (e.g., to add filtering logic or to enhance messages with additional information), monkey patching allows you to intervene in the notification process:

### Example: Monkey Patching Slack Notification Function

```python
from safe_init.slack import slack_notify as original_slack_notify

def custom_slack_notify(context_message, e, **kwargs):
    # Add custom logic here, e.g., filtering based on exception type
    if isinstance(e, ValueError):
        return  # Skip notification for ValueError
    # Modify context message
    context_message = f"Custom Prefix: {context_message}"
    # Call the original slack_notify function
    original_slack_notify(context_message, e, **kwargs)

# Monkey patch the slack_notify function
import safe_init.slack
safe_init.slack.slack_notify = custom_slack_notify
```

## Monitoring Timeouts with Tracing

Safe Init's tracing capabilities can be invaluable for monitoring and diagnosing timeouts in your Lambda functions. Here's how to leverage this feature for detailed insights into function execution times:

### Example: Enabling Function Call Tracing

```python
from safe_init.tracer import traced

# Assume this is your Lambda handler
def my_lambda_handler(event, context):
    # Your Lambda logic here
    pass

# Wrap your handler with Safe Init's tracing decorator
traced_handler = traced(my_lambda_handler)

# Set `traced_handler` as the entry point in SAFE_INIT_HANDLER
```

Or as a decorator:

```python
from safe_init.tracer import traced

@traced
def my_lambda_handler(event, context):
    # Your Lambda logic here
    pass

# Set `my_lambda_handler` as the entry point in SAFE_INIT_HANDLER
```

This setup ensures that all function calls within `my_lambda_handler` are traced, giving you visibility into potential performance bottlenecks.

## Dynamic Error Handling Strategies

While Safe Init provides a robust error handling mechanism out of the box, you might have scenarios where dynamic error handling strategies are necessary, such as different handling logic based on the exception type or context.

### Example: Custom Error Handling Logic

```python
from safe_init.decorator import safe_wrapper

# Original handler function
def my_handler(event, context):
    # Your logic here
    pass

# Custom wrapper to add error handling logic
def my_custom_error_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            # Custom handling for ValueError
            print(f"Handling ValueError: {e}")
            # Re-raise or handle the exception
        except Exception as e:
            # Fallback error handling
            raise e
    return wrapper

# Apply Safe Init's safe_wrapper and your custom error handling
wrapped_handler = safe_wrapper(my_custom_error_handler(my_handler))
```

This approach allows you to wrap your handler with both Safe Init's safety mechanisms and your custom error handling logic. It's particularly useful for scenarios where specific exceptions require unique handling beyond logging and notifications.
