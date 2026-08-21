"""Data models for the offline vehicle matcher experiment."""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class EvaluationSample:
    text: str
    entity_type: str
    expected_code: Optional[str]
    category: str


@dataclass(frozen=True)
class MatchResult:
    strategy: str
    text: str
    entity_type: str
    candidate_code: Optional[str]
    score: float
    accepted: bool
    reason: str
    method: str


@dataclass(frozen=True)
class StrategyReport:
    strategy: str
    results: Tuple[MatchResult, ...]
    precision: float
    false_positive_rate: float
    coverage: float
    abstain_rate: float
    unavailable: bool = False

