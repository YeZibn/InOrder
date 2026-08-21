from inorder_llm.context import OrderContext, OrderContextReducer
from inorder_llm.extract import Entity
from inorder_llm.normalization import normalize_vehicle_entity


def test_exact_vehicle_match_has_precedence():
    entity = normalize_vehicle_entity(Entity("vehicle_type", "set", {"value": "4.2米"}, "4.2米"))
    assert entity.attributes["value"] == "truck_4m2"
    assert entity.attributes["normalization_method"] == "exact"


def test_ensemble_accepts_high_confidence_variant():
    entity = normalize_vehicle_entity(Entity("vehicle_type", "set", {"value": "4.2米厢"}, "4.2米厢"))
    assert entity.attributes["value"] == "truck_4m2"
    assert entity.attributes["normalization_method"] == "rapidfuzz_and_ngram"
    assert entity.attributes["normalization_accepted"] is True


def test_unsafe_vehicle_does_not_overwrite_context():
    context = OrderContext(vehicle_type="truck_5m2")
    updated = OrderContextReducer().apply(context, [Entity("vehicle_type", "replace", {"value": "4米以上"}, "4米以上")])
    assert updated.vehicle_type == "truck_5m2"


def test_vehicle_types_are_not_mixed():
    entity = normalize_vehicle_entity(Entity("vehicle_specs", "set", {"value": "冷链4米2"}, "冷链4米2"))
    assert entity.attributes["normalization_accepted"] is False
