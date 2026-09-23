"""Per-worker limits for the HTTP workflow runtime."""

from dataclasses import dataclass
import math
import os
from typing import Mapping

from ..infrastructure.llm.errors import ConfigurationError


@dataclass(frozen=True)
class WorkflowRuntimeConfig:
    max_concurrency: int = 8
    max_waiting: int = 8
    queue_timeout_seconds: float = 5.0
    llm_max_concurrency: int = 8
    langextract_max_threads: int = 4
    workflow_timeout_seconds: float = 90.0

    @classmethod
    def from_environ(cls, environ: Mapping[str, str] | None = None) -> "WorkflowRuntimeConfig":
        values = os.environ if environ is None else environ
        try:
            config = cls(
                max_concurrency=int(values.get("WORKFLOW_MAX_CONCURRENCY", "8")),
                max_waiting=int(values.get("WORKFLOW_MAX_WAITING", "8")),
                queue_timeout_seconds=float(values.get("WORKFLOW_QUEUE_TIMEOUT_SECONDS", "5")),
                llm_max_concurrency=int(values.get("LLM_MAX_CONCURRENCY", "8")),
                langextract_max_threads=int(values.get("LANGEXTRACT_MAX_THREADS", "4")),
                workflow_timeout_seconds=float(values.get("WORKFLOW_TIMEOUT_SECONDS", "90")),
            )
        except (TypeError, ValueError) as exc:
            raise ConfigurationError("workflow capacity settings must be numeric") from exc
        if (
            config.max_concurrency <= 0
            or config.max_waiting < 0
            or config.llm_max_concurrency <= 0
            or config.langextract_max_threads <= 0
            or not math.isfinite(config.queue_timeout_seconds)
            or config.queue_timeout_seconds <= 0
            or not math.isfinite(config.workflow_timeout_seconds)
            or config.workflow_timeout_seconds <= 0
        ):
            raise ConfigurationError("workflow capacity limits and timeouts must be positive")
        return config
