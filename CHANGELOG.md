# Changelog

---

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
