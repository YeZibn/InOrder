from inorder_llm.catalog import (
    VEHICLE_SPECS,
    VEHICLE_TYPES,
    find_vehicle_spec,
    find_vehicle_type,
    get_vehicle_spec,
    get_vehicle_type,
    iter_vehicle_specs,
    iter_vehicle_types,
    render_vehicle_prompt_vocabulary,
)


def test_vehicle_type_catalog_has_unique_codes_and_aliases():
    codes = [item.code for item in VEHICLE_TYPES]
    aliases = [alias for item in VEHICLE_TYPES for alias in item.aliases]
    assert len(codes) == len(set(codes))
    assert len(aliases) == len(set(aliases))
    assert all(item.status == "active" for item in VEHICLE_TYPES)


def test_vehicle_type_catalog_contains_base_types_and_all_standard_lengths():
    assert find_vehicle_type("小拉").code == "four_wheel_small"
    assert find_vehicle_type("小面包").code == "small_van"
    assert find_vehicle_type("面包车").code == "medium_van"

    lengths = [item for item in VEHICLE_TYPES if item.length_cm is not None]
    assert [item.code for item in lengths] == [
        "truck_3m8", "truck_4m2", "truck_5m2", "truck_6m2", "truck_6m8",
        "truck_7m6", "truck_8m2", "truck_8m6", "truck_9m6", "truck_11m7",
        "truck_12m5", "truck_13m", "truck_13m7", "truck_15m", "truck_16m",
        "truck_17m5",
    ]
    assert get_vehicle_type("truck_4m2").length_cm == 420
    assert find_vehicle_type("4.2 米").code == "truck_4m2"


def test_vehicle_specs_catalog_contains_confirmed_specs_and_groups():
    assert [item.code for item in VEHICLE_SPECS] == [
        "cold_chain", "enclosed", "high_rail", "flatbed", "dangerous_goods",
        "high_roof", "tail_lift",
    ]
    assert find_vehicle_spec("冷藏车").code == "cold_chain"
    assert find_vehicle_spec("带尾板").code == "tail_lift"
    assert get_vehicle_spec("high_roof").group == "structure"
    assert get_vehicle_spec("dangerous_goods").group == "transport_requirement"


def test_catalog_readers_are_stable_and_do_not_infer_ambiguous_values():
    assert iter_vehicle_types() is VEHICLE_TYPES
    assert iter_vehicle_specs() is VEHICLE_SPECS


def test_prompt_vocabulary_is_rendered_from_catalog_labels_and_aliases():
    prompt = render_vehicle_prompt_vocabulary()
    assert "4米2（truck_4m2）：4米2、四米二、4.2米" in prompt
    assert "冷链（cold_chain）：冷链、冷链车、冷藏车" in prompt
    assert find_vehicle_type("之前那个车") is None
    assert find_vehicle_type("4米以上") is None
    assert find_vehicle_spec("冷链4米2") is None
