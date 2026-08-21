from inorder_llm.catalog import find_vehicle_keyword, iter_vehicle_keywords
from inorder_llm.vehicle_matching import (
    EVALUATION_SAMPLES, EnsembleMatcher, NgramMatcher, RapidFuzzMatcher,
    evaluate, render_report,
)


def test_dataset_covers_required_categories():
    assert len(EVALUATION_SAMPLES) == 500
    categories = {sample.category for sample in EVALUATION_SAMPLES}
    assert {"positive_variant", "catalog_alias", "short_confusion", "numeric_conflict", "range"} <= categories


def test_ngram_rejects_business_exclusions_and_numeric_conflict():
    matcher = NgramMatcher()
    assert not matcher.match("4米以上", "vehicle_type").accepted
    assert not matcher.match("之前那个车", "vehicle_type").accepted
    assert not matcher.match("4米3", "vehicle_type").accepted


def test_experiment_does_not_change_catalog():
    before = tuple((x.entity_type, x.code, x.keywords) for x in iter_vehicle_keywords())
    evaluate(EVALUATION_SAMPLES)
    after = tuple((x.entity_type, x.code, x.keywords) for x in iter_vehicle_keywords())
    assert before == after
    assert find_vehicle_keyword("4.2米", "vehicle_type").code == "truck_4m2"


def test_reports_have_comparable_metrics():
    reports = evaluate(EVALUATION_SAMPLES)
    assert [r.strategy for r in reports] == ["rapidfuzz", "ngram", "ensemble"]
    assert all(0 <= r.precision <= 1 and 0 <= r.false_positive_rate <= 1 for r in reports)
    assert "false_positive_rate" in render_report(reports)


def test_rapidfuzz_missing_dependency_is_a_safe_abstention():
    matcher = RapidFuzzMatcher()
    result = matcher.match("4.2m", "vehicle_type")
    if not matcher.available:
        assert result.reason == "dependency_missing"
