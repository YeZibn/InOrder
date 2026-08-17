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


def load_config(environ=None) -> LLMConfig:
    if environ is None and load_dotenv is not None:
        load_dotenv()
    env = os.environ if environ is None else environ
    missing = [key for key in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL") if not env.get(key)]
    if missing:
        raise ConfigurationError("Missing required LLM configuration: " + ", ".join(missing))
    try:
        timeout = float(env.get("LLM_TIMEOUT", "30"))
        max_retries = int(env.get("LLM_MAX_RETRIES", "2"))
        backoff = float(env.get("LLM_BACKOFF_SECONDS", "0.5"))
    except ValueError as exc:
        raise ConfigurationError("LLM_TIMEOUT, LLM_MAX_RETRIES and LLM_BACKOFF_SECONDS must be numeric") from exc
    if timeout <= 0 or max_retries < 0 or backoff < 0:
        raise ConfigurationError("LLM timeout must be positive and retry values cannot be negative")
    reasoning_effort = env.get("LLM_REASONING_EFFORT") or None
    if reasoning_effort not in (None, "low", "medium", "high"):
        raise ConfigurationError("LLM_REASONING_EFFORT must be one of: low, medium, high")
    extractor_backend = env.get("EXTRACTOR_BACKEND", "langextract")
    if extractor_backend not in ("langextract", "json"):
        raise ConfigurationError("EXTRACTOR_BACKEND must be one of: langextract, json")
    return LLMConfig(
        env["LLM_API_KEY"],
        env["LLM_BASE_URL"],
        env["LLM_MODEL"],
        timeout,
        max_retries,
        backoff,
        reasoning_effort,
        extractor_backend,
    )
