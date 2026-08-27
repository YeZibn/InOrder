from dataclasses import dataclass
import os

from .errors import ConfigurationError

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    timeout: float = 30.0
    max_retries: int = 2
    backoff_seconds: float = 0.5
    reasoning_effort: str = None
    extractor_backend: str = "langextract"
    api_mode: str = "chat_completions"
    streaming: bool = False
    backoff_max_seconds: float = 8.0
    workflow_timeout_seconds: float = 90.0
    # Provider is appended to preserve compatibility with existing positional
    # construction of LLMConfig(api_key, base_url, model, ...).
    provider: str = "openai"


def load_config(environ=None) -> LLMConfig:
    if environ is None and load_dotenv is not None:
        load_dotenv()
    env = os.environ if environ is None else environ
    provider = env.get("LLM_PROVIDER", "openai").strip().lower()
    if provider not in ("openai", "deepseek"):
        raise ConfigurationError("LLM_PROVIDER must be one of: openai, deepseek")
    provider_key = env.get(f"LLM_API_KEY_{provider.upper()}")
    api_key = provider_key or env.get("LLM_API_KEY")
    if not api_key:
        raise ConfigurationError(
            f"Missing required LLM configuration: LLM_API_KEY_{provider.upper()}"
            f" (or LLM_API_KEY as fallback)"
        )
    if not env.get("LLM_MODEL"):
        raise ConfigurationError("Missing required LLM configuration: LLM_MODEL")
    default_base_url = {
        "openai": "https://api.openai.com/v1",
        "deepseek": "https://api.deepseek.com",
    }[provider]
    base_url = env.get("LLM_BASE_URL") or default_base_url
    normalized_base_url = base_url.strip().rstrip("/")
    if not normalized_base_url:
        raise ConfigurationError("LLM_BASE_URL must be a non-empty service root")
    if normalized_base_url.endswith(("/chat/completions", "/responses")):
        raise ConfigurationError("LLM_BASE_URL must be a service root, not a concrete endpoint")
    try:
        timeout = float(env.get("LLM_TIMEOUT", "30"))
        max_retries = int(env.get("LLM_MAX_RETRIES", "2"))
        backoff = float(env.get("LLM_BACKOFF_SECONDS", "0.5"))
        backoff_max = float(env.get("LLM_BACKOFF_MAX_SECONDS", "8"))
        workflow_timeout = float(env.get("WORKFLOW_TIMEOUT_SECONDS", "90"))
    except ValueError as exc:
        raise ConfigurationError("LLM timeout and retry settings must be numeric") from exc
    if timeout <= 0 or max_retries < 0 or backoff < 0 or backoff_max < 0 or workflow_timeout <= 0:
        raise ConfigurationError("LLM timeout must be positive and retry values cannot be negative")
    reasoning_effort = env.get("LLM_REASONING_EFFORT") or None
    if reasoning_effort not in (None, "low", "medium", "high", "max"):
        raise ConfigurationError("LLM_REASONING_EFFORT must be one of: low, medium, high, max")
    extractor_backend = env.get("EXTRACTOR_BACKEND", "langextract")
    if extractor_backend not in ("langextract", "json"):
        raise ConfigurationError("EXTRACTOR_BACKEND must be one of: langextract, json")
    api_mode = env.get("LLM_API_MODE", "chat_completions").strip().lower()
    if api_mode not in ("chat_completions", "responses"):
        raise ConfigurationError("LLM_API_MODE must be one of: chat_completions, responses")
    streaming_value = env.get("LLM_STREAMING", "false").strip().lower()
    if streaming_value not in ("true", "false", "1", "0", "yes", "no", "on", "off"):
        raise ConfigurationError("LLM_STREAMING must be a boolean")
    return LLMConfig(
        api_key,
        normalized_base_url,
        env["LLM_MODEL"],
        timeout,
        max_retries,
        backoff,
        reasoning_effort,
        extractor_backend,
        api_mode,
        streaming_value in ("true", "1", "yes", "on"),
        backoff_max,
        workflow_timeout,
        provider,
    )
