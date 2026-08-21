"""Evaluation metrics and deterministic text report."""

from typing import Iterable, List, Sequence
from .models import EvaluationSample, MatchResult, StrategyReport
from .matchers import EnsembleMatcher, NgramMatcher, RapidFuzzMatcher


def evaluate_strategy(samples: Sequence[EvaluationSample], matcher) -> StrategyReport:
    results = tuple(matcher.match(s.text, s.entity_type) for s in samples)
    accepted = [r for r in results if r.accepted]
    correct = sum(r.accepted and r.candidate_code == s.expected_code for r, s in zip(results, samples))
    false_accept = sum(r.accepted and s.expected_code is None for r, s in zip(results, samples))
    precision = correct / len(accepted) if accepted else 0.0
    negatives = sum(s.expected_code is None for s in samples)
    fpr = false_accept / negatives if negatives else 0.0
    coverage = len(accepted) / len(samples) if samples else 0.0
    return StrategyReport(matcher.strategy, results, precision, fpr, coverage, 1.0 - coverage, getattr(matcher, "_unavailable", None) is not None)


def evaluate(samples: Sequence[EvaluationSample]) -> List[StrategyReport]:
    return [evaluate_strategy(samples, matcher) for matcher in (RapidFuzzMatcher(), NgramMatcher(), EnsembleMatcher())]


def render_report(reports: Iterable[StrategyReport]) -> str:
    lines = ["strategy | precision | false_positive_rate | coverage | abstain_rate", "--- | ---: | ---: | ---: | ---:"]
    for report in reports:
        lines.append(f"{report.strategy} | {report.precision:.3f} | {report.false_positive_rate:.3f} | {report.coverage:.3f} | {report.abstain_rate:.3f}")
    return "\n".join(lines)

