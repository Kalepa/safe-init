# Troubleshooting

In this section, we address common issues you might encounter while using Safe Init, along with detailed explanations and solutions. Additionally, we delve into the configuration options provided by Safe Init, explaining their purposes, potential impacts, and how to effectively use them to enhance your application's error handling and logging.

## Common Issues

### Safe Init Handler Not Triggered

**Symptom:** Your Lambda function executes, but it seems like Safe Init's error handling and logging features aren't being utilized.

**Possible Causes and Solutions:**

- **Misconfigured Lambda Handler:** Ensure that your Lambda function's handler is set to `safe_init.handler.handler` in your function's configuration.
- **Incorrect `SAFE_INIT_HANDLER` Value:** The `SAFE_INIT_HANDLER` environment variable should point to your original handler function, including the module name. For example, `my_module.my_handler`.

### Errors Not Reported to Sentry

**Symptom:** Exceptions aren't being logged to Sentry, despite the configuration seeming correct.

**Possible Causes and Solutions:**

- **Missing Sentry DSN:** Ensure the `SENTRY_DSN` environment variable is correctly set with your Sentry project's DSN.
- **Sentry SDK Initialization:** Sentry SDK might not be initializing correctly within Safe Init. This can happen if the SDK was manually initialized in your code but not detected by Safe Init. Remove manual Sentry SDK initialization from your code, or ensure Safe Init detects it by not setting `SAFE_INIT_NO_DETECT_UNINITIALIZED_SENTRY`.

### Slack Notifications Not Received

**Symptom:** Slack notifications are configured but not received upon errors.

**Possible Causes and Solutions:**

- **Slack Webhook URL:** Confirm that `SAFE_INIT_SLACK_WEBHOOK_URL` is correctly set to your Slack incoming webhook URL. If setting it programmatically via `safe_init.slack.safe_init_slack_webhook_url`, ensure this is done before Safe Init handles an error.
- **Network Issues:** If your Lambda function runs in a VPC without Internet access, it cannot reach Slack's servers. Ensure your VPC configuration allows for external HTTP/S requests.

### Datadog Metrics Not Available

**Symptom:** Expected metrics are not appearing in Datadog.

**Possible Causes and Solutions:**

- **Datadog Lambda Layer:** Verify that the Datadog Lambda Layer is applied to your Lambda function. Safe Init attempts to integrate with Datadog automatically, but this requires the Datadog Lambda Layer to be present.
- **`SAFE_INIT_NO_DATADOG_WRAPPER` Set:** If this environment variable is set to `'true'`, Safe Init will not integrate with Datadog. Ensure this is not set if you wish to use Datadog.
