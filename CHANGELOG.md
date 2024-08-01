# Changelog

---

## v1.2.1 (2024-08-01)
### Improvements
- Safe Init will no longer add the configured AWS Secrets Manager secret ARN prefix to the specified value if it already contains a prefix.

## v1.2.0 (2024-07-29)
### BREAKING CHANGES
- Setting Slack webhook URLs and custom loggers using monkey patching wasn't working reliably and is no longer supported. Instead, use ContextVars to set your desired values and Safe Init will read them automatically.

### Improvements
- Fixed Slack notifications not being sent when Safe Init couldn't gather enough information to identify function execution context.

## v1.1.6 (2024-07-25)
### Improvements
- Added a new option (`SAFE_INIT_ALWAYS_NOTIFY_SLACK`) that enables Safe Init to notify Slack about failures even if a Sentry notification has been sent successfully.

## v1.1.5 (2024-07-24)
### Bug fixes
- Fixed a bug where the value of an AWS Secrets Manager secret wasn't always returned as a string.

## v1.1.4 (2024-07-22)
### New features
- Added a new option that allows specifying a common ARN prefix for all secrets using the `SAFE_INIT_SECRET_ARN_PREFIX` environment variable.

### Bug fixes
- Fixed a bug where a KeyError could be raised if an environment variable was no longer found after function import phase.

## v1.1.3 (2024-06-10)
### Bug fixes
- Fixed a bug where setting environment variables to a false-like value (e.g. `0`, `false`, `off`, `no`) would not work as expected.

## v1.1.2 (2024-05-07)
### Bug fixes
- Fixed a bug where resolved AWS Secrets Manager secrets were being accessible during the initialization, but not during the execution of the Lambda function.

## v1.1.1 (2024-05-07)
No significant changes.

## v1.1.0 (2024-05-07)
### New features
- AWS Secrets integration: Safe Init can now automatically fetch secrets from AWS Secrets Manager and inject them into your Lambda function's environment variables.

## v1.0.2 (2024-04-12)
### Improvements
- Timeout notifications now include additional tags and attachments in Sentry events.
- Added tags to uncaught exception events in Sentry.

### Documentation
- Updated `README.md` with screenshots of Slack notifications.

## v1.0.1 (2024-04-11)
### Improvements
- Added Lambda function name to timeout notification logs and Sentry events.
- Updated package compatibility with `ddtrace` and `datadog-lambda` to all available versions.

### Documentation
- Updated `README.md` and documentation site with quick links to GitHub, PyPI and the documentation site.

## v1.0.0 (2024-03-25)

- **First Public Release**!
