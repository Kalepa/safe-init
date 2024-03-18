from safe_init.tracer import FunctionCallSummary


class SafeInitError(Exception):
    """
    An exception that is raised when there is an error initializing the Lambda handler function.
    """


class SafeInitTimeoutWarning(TimeoutError):  # noqa: N818
    """
    An exception that is raised when the Lambda handler function times out.
    """

    traces: list[FunctionCallSummary] = []  # noqa: RUF012


class SafeInitMissingSentryWarning(ImportWarning):
    """
    An exception that is raised when the Lambda handler does not initialize the Sentry SDK.
    """


class SafeInitInitPhaseTimeoutWarning(ImportWarning):
    """
    An exception that is raised when the init (import) phase of a Lambda function is executed more than once.
    """
