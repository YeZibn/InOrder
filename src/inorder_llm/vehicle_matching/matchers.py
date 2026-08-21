"""Conservative candidate matchers used only by the offline experiment."""

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Iterable, List, Optional, Tuple

from inorder_llm.catalog import VehicleKeyword, find_vehicle_keyword, iter_vehicle_keywords, normalize_vehicle_keyword
from .models import MatchResult


class MatcherUnavailableError(RuntimeError):
    pass


_REJECT_RE = re.compile(r"(以上|以下|左右|大约|约|超过|不少于|至少|之前|上次|那个|这辆|这种|小车$|大车$|货车$|卡车$)")
_NUMBER_RE = re.compile(r"(?<![0-9])([0-9]+(?:[.．][0-9]+)?)(?:米|m)([0-9])?", re.I)


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").strip().lower().replace(" ", "")
    return normalize_vehicle_keyword(text)


def _number(text: str) -> Optional[float]:
    m = _NUMBER_RE.search(_clean(text))
    if not m:
        return None
    value = float(m.group(1).replace("．", "."))
    # Chinese truck lengths are commonly written as ``4米2`` (= 4.2m).
    if m.group(2) and "." not in m.group(1):
        value += int(m.group(2)) / 10
    return value


def _guard(text: str, keyword: VehicleKeyword) -> Optional[str]:
    if len(_clean(text)) < 3:
        return "short_input"
    if _REJECT_RE.search(_clean(text)):
        return "excluded_semantics"
    source_number = _number(text)
    candidate_numbers = [_number(alias) for alias in keyword.keywords]
    candidate_number = next((n for n in candidate_numbers if n is not None), None)
    if keyword.entity_type == "vehicle_specs" and source_number is not None:
        return "mixed_entity_expression"
    if source_number is not None and candidate_number is not None and source_number != candidate_number:
        return "numeric_conflict"
    return None


def _candidates(entity_type: str) -> List[VehicleKeyword]:
    return [x for x in iter_vehicle_keywords() if x.entity_type == entity_type and x.enabled]


class _BaseMatcher:
    strategy = "base"
    method = "base"

    def __init__(self, threshold: float = 80.0, gap: float = 5.0):
        self.threshold, self.gap = threshold, gap

    def _result(self, text: str, entity_type: str, scored: List[Tuple[float, VehicleKeyword]]) -> MatchResult:
        scored.sort(key=lambda x: (-x[0], x[1].code))
        best_score, best = scored[0] if scored else (0.0, None)
        second = scored[1][0] if len(scored) > 1 else 0.0
        if best is None:
            return MatchResult(self.strategy, text, entity_type, None, 0.0, False, "no_candidate", self.method)
        guard = _guard(text, best)
        accepted = best_score >= self.threshold and (best_score - second >= self.gap) and guard is None
        reason = guard or ("below_threshold" if best_score < self.threshold else "candidate_gap")
        return MatchResult(self.strategy, text, entity_type, best.code if accepted else best.code, round(best_score, 3), accepted, reason, self.method)


class RapidFuzzMatcher(_BaseMatcher):
    strategy, method = "rapidfuzz", "rapidfuzz_ratio"

    def __init__(self, threshold: float = 82.0, gap: float = 5.0):
        super().__init__(threshold, gap)
        try:
            from rapidfuzz.fuzz import ratio
        except ImportError as exc:
            self._ratio = None
            self._unavailable = exc
        else:
            self._ratio, self._unavailable = ratio, None

    @property
    def available(self) -> bool:
        return self._ratio is not None

    def match(self, text: str, entity_type: str) -> MatchResult:
        if not self.available:
            return MatchResult(self.strategy, text, entity_type, None, 0.0, False, "dependency_missing", self.method)
        scored = [(max(self._ratio(_clean(text), _clean(alias)) for alias in item.keywords), item) for item in _candidates(entity_type)]
        return self._result(text, entity_type, scored)


def _ngrams(text: str, n: int) -> set:
    text = _clean(text)
    return {text[i:i+n] for i in range(len(text) - n + 1)} if len(text) >= n else set()


def _ngram_score(left: str, right: str) -> float:
    scores = []
    for n in (2, 3):
        a, b = _ngrams(left, n), _ngrams(right, n)
        scores.append(100.0 * (2 * len(a & b) / (len(a) + len(b))) if a and b else 0.0)
    return max(scores)


class NgramMatcher(_BaseMatcher):
    strategy, method = "ngram", "char_bigram_trigram"

    def match(self, text: str, entity_type: str) -> MatchResult:
        scored = [(max(_ngram_score(text, alias) for alias in item.keywords), item) for item in _candidates(entity_type)]
        return self._result(text, entity_type, scored)


class EnsembleMatcher(_BaseMatcher):
    strategy, method = "ensemble", "rapidfuzz_and_ngram"

    def __init__(self, rapid: Optional[RapidFuzzMatcher] = None, ngram: Optional[NgramMatcher] = None):
        super().__init__()
        self.rapid, self.ngram = rapid or RapidFuzzMatcher(), ngram or NgramMatcher()

    def match(self, text: str, entity_type: str) -> MatchResult:
        r, n = self.rapid.match(text, entity_type), self.ngram.match(text, entity_type)
        if not self.rapid.available:
            return MatchResult(self.strategy, text, entity_type, None, n.score, False, "dependency_missing", self.method)
        if r.candidate_code != n.candidate_code or not r.accepted or not n.accepted:
            return MatchResult(self.strategy, text, entity_type, None, min(r.score, n.score), False, "candidate_disagreement_or_guard", self.method)
        return MatchResult(self.strategy, text, entity_type, r.candidate_code, min(r.score, n.score), True, "accepted", self.method)
