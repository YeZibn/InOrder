class LLMError(Exception):
    """Base class for safe, application-level LLM errors."""

    retryable = False


class ConfigurationError(LLMError):
    pass


class InvalidRequestError(LLMError):
    pass


class AuthenticationError(LLMError):
    pass


class RateLimitError(LLMError):
    retryable = True

    def __init__(self, message="LLM rate limit exceeded", retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class TimeoutError(LLMError):
    retryable = True


class UpstreamError(LLMError):
    retryable = True


class UpstreamFatalError(LLMError):
    """An upstream failure without evidence that retrying is safe."""

    retryable = False


class WorkflowTimeoutError(LLMError):
    """The current Python workflow exceeded its request deadline."""

    retryable = False


class WorkflowOverloadedError(LLMError):
    """The API worker has no capacity within its bounded wait period."""

    retryable = True


class NodeExecutionError(LLMError):
    """A node failed outside the LLM transport layer."""

    retryable = False
