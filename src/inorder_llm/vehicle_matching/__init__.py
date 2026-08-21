"""Offline vehicle fuzzy-matching evaluation tools.

This package is deliberately separate from production normalization.  It only
reads :mod:`inorder_llm.catalog` and returns evaluation records.
"""

from .models import MatchResult, EvaluationSample, StrategyReport
from .dataset import EVALUATION_SAMPLES, build_evaluation_samples
from .matchers import NgramMatcher, RapidFuzzMatcher, EnsembleMatcher, MatcherUnavailableError
from .evaluation import evaluate, evaluate_strategy, render_report

__all__ = [
    "MatchResult", "EvaluationSample", "StrategyReport",
    "EVALUATION_SAMPLES", "build_evaluation_samples",
    "NgramMatcher", "RapidFuzzMatcher", "EnsembleMatcher",
    "MatcherUnavailableError", "evaluate", "evaluate_strategy", "render_report",
]
