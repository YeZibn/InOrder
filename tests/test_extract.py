import json

import pytest

from inorder_llm.extract import (
    Entity,
    EXTRACTION_SYSTEM_PROMPT,
    extract_entities,
    parse_entities,
)
from inorder_llm.intent.resolver import StructuredIntentError


class _Resp:
    def __init__(self, text):
        self.text = text


class FakeLLMClient:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def chat(self, messages):
        self.calls.append(list(messages))
        return _Resp(self.text)


# --- prompt 内容断言 ---

def test_prompt_defines_action_enum_and_judgment_rules():
    p = EXTRACTION_SYSTEM_PROMPT
    for a in ("add", "set", "remove", "replace"):
        assert a in p
    assert "累加" in p and "覆盖" in p and "删除" in p and "替换" in p
    assert "entities" in p


def test_prompt_covers_fourteen_entity_types():
    p = EXTRACTION_SYSTEM_PROMPT
    for t in ("time", "location", "person", "phone", "vehicle_type",
              "vehicle_specs", "cargo", "follow_car_number", "oneself_follow_flag",
              "invoice_type", "payment_type", "service_type", "remark", "order_id"):
        assert t in p


def test_prompt_contains_normalization_rules():
    p = EXTRACTION_SYSTEM_PROMPT
    assert "上午" in p and "06:00-12:00" in p
    assert "小面" in p and "面包车" in p
    assert "surname" in p
    assert "full_address" in p
    assert "不得从上下文补全" in p


def test_prompt_separates_vehicle_types_and_specs():
    p = EXTRACTION_SYSTEM_PROMPT
    for code in ("truck_4m2", "cold_chain", "enclosed", "high_rail", "flatbed",
                 "dangerous_goods", "high_roof", "tail_lift"):
        assert code in p
    assert "不得输出为 `vehicle_type`" in p
    assert "多个规格必须各输出一个独立的 `vehicle_specs` entity" in p
    assert "X米以上" in p and "不要在此处推导" in p


def test_prompt_vehicle_examples_preserve_text_and_use_catalog_codes():
    p = EXTRACTION_SYSTEM_PROMPT
    assert '"extraction_text":"冷链车","attributes":{"value":"cold_chain"}' in p
    assert '"extraction_text":"4米2","attributes":{"value":"truck_4m2"}' in p
    assert '"extraction_text":"带尾板","attributes":{"value":"tail_lift"}' in p


def test_prompt_contains_action_few_shot_examples():
    p = EXTRACTION_SYSTEM_PROMPT
    for a in ('"action":"add"', '"action":"set"', '"action":"remove"', '"action":"replace"'):
        assert a in p


# --- 4.1 action 四类提取 ---

def test_extract_add_action():
    payload = {"entities": [{"type": "cargo", "action": "add", "extraction_text": "一吨苹果",
                             "attributes": {"name": "苹果", "weight": "1吨"}}]}
    client = FakeLLMClient(json.dumps(payload))
    entities = extract_entities(client, "再加一吨苹果", [], "2026-08-14 10:00")
    assert len(entities) == 1
    assert entities[0].action == "add"
    assert entities[0].type == "cargo"
    assert entities[0].attributes["name"] == "苹果"


def test_extract_set_action():
    payload = {"entities": [{"type": "cargo", "action": "set", "extraction_text": "两吨苹果",
                             "attributes": {"name": "苹果", "weight": "2吨"}}]}
    client = FakeLLMClient(json.dumps(payload))
    entities = extract_entities(client, "我要两吨苹果", [], "2026-08-14 10:00")
    assert entities[0].action == "set"


def test_extract_remove_action():
    payload = {"entities": [{"type": "cargo", "action": "remove", "extraction_text": "苹果",
                             "attributes": {"name": "苹果"}}]}
    client = FakeLLMClient(json.dumps(payload))
    entities = extract_entities(client, "苹果不要了", [], "2026-08-14 10:00")
    assert entities[0].action == "remove"


def test_extract_replace_action():
    payload = {"entities": [{"type": "vehicle_specs", "action": "replace", "extraction_text": "冷链车",
                             "attributes": {"value": "cold_chain"}}]}
    client = FakeLLMClient(json.dumps(payload))
    entities = extract_entities(client, "车型规格换成冷链车", [], "2026-08-14 10:00")
    assert entities[0].action == "replace"
    assert entities[0].type == "vehicle_specs"
    assert entities[0].attributes["value"] == "cold_chain"


# --- 4.2 实体类型覆盖与归一 ---

def test_extract_location_with_roles():
    payload = {"entities": [
        {"type": "location", "action": "set", "extraction_text": "上海", "attributes": {"role": "pickup", "city": "上海"}},
        {"type": "location", "action": "set", "extraction_text": "温州", "attributes": {"role": "dropoff", "city": "温州"}},
    ]}
    client = FakeLLMClient(json.dumps(payload))
    entities = extract_entities(client, "从上海运到温州", [], "2026-08-14 10:00")
    assert len(entities) == 2
    assert entities[0].attributes["role"] == "pickup"
    assert entities[1].attributes["role"] == "dropoff"


def test_extract_location_preserves_city_and_full_address():
    payload = {"entities": [
        {
            "type": "location",
            "action": "set",
            "extraction_text": "上海浦东金桥物流园3号仓库",
            "attributes": {
                "role": "pickup",
                "city": "上海",
                "full_address": "上海浦东金桥物流园3号仓库",
            },
        },
        {
            "type": "location",
            "action": "set",
            "extraction_text": "温州瓯海批发市场",
            "attributes": {
                "role": "dropoff",
                "city": "温州",
                "full_address": "温州瓯海批发市场",
            },
        },
    ]}
    entities = extract_entities(
        FakeLLMClient(json.dumps(payload, ensure_ascii=False)),
        "从上海浦东金桥物流园3号仓库运到温州瓯海批发市场",
        [],
        "2026-08-14 10:00",
    )
    assert entities[0].attributes["city"] == "上海"
    assert entities[0].attributes["full_address"] == "上海浦东金桥物流园3号仓库"
    assert entities[1].attributes["full_address"] == "温州瓯海批发市场"


def test_extract_location_without_city_keeps_explicit_full_address():
    payload = {"entities": [{
        "type": "location",
        "action": "set",
        "extraction_text": "浦东金桥物流园",
        "attributes": {
            "role": "pickup",
            "full_address": "浦东金桥物流园",
        },
    }]}
    entities = extract_entities(
        FakeLLMClient(json.dumps(payload, ensure_ascii=False)),
        "从浦东金桥物流园装货",
        [],
        "2026-08-14 10:00",
    )
    assert entities[0].attributes.get("city") is None
    assert entities[0].attributes["full_address"] == "浦东金桥物流园"


def test_extract_location_rejects_full_address_outside_source():
    payload = {"entities": [{
        "type": "location",
        "action": "set",
        "extraction_text": "上海",
        "attributes": {
            "role": "pickup",
            "city": "上海",
            "full_address": "上海浦东某仓库",
        },
    }]}
    with pytest.raises(StructuredIntentError, match="full_address"):
        extract_entities(
            FakeLLMClient(json.dumps(payload, ensure_ascii=False)),
            "从上海装货",
            [],
            "2026-08-14 10:00",
        )


def test_extract_vehicle_type_normalized_value():
    payload = {"entities": [{"type": "vehicle_type", "action": "set", "extraction_text": "中面",
                             "attributes": {"extraction_text": "中面"}}]}
    client = FakeLLMClient(json.dumps(payload))
    entities = extract_entities(client, "来个面包车", [], "2026-08-14 10:00")
    assert entities[0].extraction_text == "中面"


def test_extract_cargo_attributes():
    payload = {"entities": [{"type": "cargo", "action": "set", "extraction_text": "两吨苹果",
                             "attributes": {"name": "苹果", "weight": "2吨", "quantity": "2"}}]}
    client = FakeLLMClient(json.dumps(payload))
    entities = extract_entities(client, "两吨苹果", [], "2026-08-14 10:00")
    assert entities[0].attributes["weight"] == "2吨"


def test_extract_time_with_history_context():
    payload = {"entities": [{"type": "time", "action": "set", "extraction_text": "上周",
                             "attributes": {"context": "history", "start": "", "end": "2026-08-07 10:00"}}]}
    client = FakeLLMClient(json.dumps(payload))
    entities = extract_entities(client, "查上周订单", [], "2026-08-14 10:00")
    assert entities[0].attributes["context"] == "history"


# --- 4.3 解析健壮性 ---

def test_extract_invalid_json_raises():
    client = FakeLLMClient("not json")
    with pytest.raises(StructuredIntentError):
        extract_entities(client, "hi", [], "2026-08-14 10:00")


def test_parse_invalid_action_raises():
    payload = {"entities": [{"type": "cargo", "action": "append", "extraction_text": "x", "attributes": {}}]}
    with pytest.raises(StructuredIntentError):
        parse_entities(payload)


def test_parse_missing_field_raises():
    payload = {"entities": [{"type": "cargo", "action": "add", "attributes": {}}]}
    with pytest.raises(StructuredIntentError):
        parse_entities(payload)


def test_parse_entities_not_array_raises():
    with pytest.raises(StructuredIntentError):
        parse_entities({"entities": "not array"})


def test_parse_entity_not_object_raises():
    payload = {"entities": ["not object"]}
    with pytest.raises(StructuredIntentError):
        parse_entities(payload)


def test_parse_attributes_not_object_raises():
    payload = {"entities": [{"type": "cargo", "action": "add", "extraction_text": "x", "attributes": "not obj"}]}
    with pytest.raises(StructuredIntentError):
        parse_entities(payload)


# --- 4.4 输入参数 ---

def test_extract_empty_history_allowed():
    payload = {"entities": []}
    client = FakeLLMClient(json.dumps(payload))
    entities = extract_entities(client, "你好", [], "2026-08-14 10:00")
    assert entities == []


def test_extract_reference_time_injected_with_weekday():
    payload = {"entities": []}
    client = FakeLLMClient(json.dumps(payload))
    extract_entities(client, "下单", [], "2026-08-14 10:00")
    user_msg = client.calls[0][1].content
    assert "【参考时间】2026-08-14 10:00（星期五）" in user_msg
    assert "下单" in user_msg


def test_extract_history_injected_into_user_message():
    payload = {"entities": []}
    client = FakeLLMClient(json.dumps(payload))
    history = [
        {"role": "user", "content": "我要下单从上海运货到温州"},
        {"role": "assistant", "content": "已创建草稿"},
    ]
    extract_entities(client, "上次那个再发一单", history, "2026-08-14 10:00")
    user_msg = client.calls[0][1].content
    assert "【对话历史】" not in user_msg
    assert "我要下单从上海运货到温州" not in user_msg
    assert "已创建草稿" not in user_msg
    assert "上次那个再发一单" in user_msg


def test_extract_sends_system_then_user_message():
    payload = {"entities": []}
    client = FakeLLMClient(json.dumps(payload))
    extract_entities(client, "hi", [], "2026-08-14 10:00")
    messages = client.calls[0]
    assert [m.role for m in messages] == ["system", "user"]
    assert messages[0].content == EXTRACTION_SYSTEM_PROMPT


def test_entity_to_dict_roundtrip():
    e = Entity(type="cargo", action="add", attributes={"name": "苹果"}, extraction_text="一吨苹果")
    d = e.to_dict()
    assert d == {"type": "cargo", "action": "add", "attributes": {"name": "苹果"}, "extraction_text": "一吨苹果"}
