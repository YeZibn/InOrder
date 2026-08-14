class LLMError(Exception):
    """Base class for safe, application-level LLM errors."""


class ConfigurationError(LLMError):
    pass


class InvalidRequestError(LLMError):
    pass


class AuthenticationError(LLMError):
    pass


class RateLimitError(LLMError):
    def __init__(self, message="LLM rate limit exceeded", retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class TimeoutError(LLMError):
    pass


class UpstreamError(LLMError):
    pass
