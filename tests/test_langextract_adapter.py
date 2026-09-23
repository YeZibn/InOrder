import os

import pytest

from inorder_llm.extract import GroundedExtraction, LangExtractEntityExtractor, map_grounded_extractions
from inorder_llm.context import OrderContext, OrderContextReducer
from inorder_llm.extract import Entity
from inorder_llm.infrastructure.llm import ConfigurationError, LLMConfig, load_config
from inorder_llm.intent.resolver import StructuredIntentError
from inorder_llm.extract.resolver import build_langextract_order_examples, format_langextract_source


def test_mapper_preserves_grounded_text_and_action_attributes():
    entities = map_grounded_extractions(
        [GroundedExtraction("cargo", "一吨苹果", {"name": "苹果", "weight": "1吨", "action": "set"}, {"char_start": 2, "char_end": 6})],
        "新增一吨苹果",
    )
    assert entities[0].type == "cargo"
    assert entities[0].action == "set"
    assert entities[0].attributes["action"] == "set"
    assert entities[0].extraction_text == "一吨苹果"


def test_mapper_preserves_llm_semantic_attributes_without_inference():
    entities = map_grounded_extractions(
        [
            GroundedExtraction("location", "温州市", {"role": "dropoff", "city": "温州市", "action": "replace"}),
            GroundedExtraction("cargo", "苹果", {"name": "苹果", "action": "remove"}),
        ],
        "从温州运往上海",
    )
    assert entities[0].type == "location"
    assert entities[0].action == "replace"
    assert entities[0].attributes == {"role": "dropoff", "city": "温州市", "action": "replace"}
    assert entities[1].attributes == {"name": "苹果", "action": "remove"}


def test_mapper_preserves_vehicle_source_without_catalog_conversion():
    entities = map_grounded_extractions(
        [GroundedExtraction("vehicle_type", "4.2米", {"value": "4.2米", "action": "set"})],
        "4.2米",
    )
    assert entities[0].extraction_text == "4.2米"
    assert entities[0].attributes["value"] == "4.2米"


def test_mapper_preserves_location_city_and_full_address():
    entities = map_grounded_extractions(
        [
            GroundedExtraction(
                "location",
                "上海浦东金桥物流园3号仓库",
                {
                    "role": "pickup",
                    "city": "上海",
                    "full_address": "上海浦东金桥物流园3号仓库",
                    "action": "set",
                },
            )
        ],
        "从上海浦东金桥物流园3号仓库装货",
    )
    assert entities[0].attributes["city"] == "上海"
    assert entities[0].attributes["full_address"] == "上海浦东金桥物流园3号仓库"


def test_mapper_preserves_explicit_location_province():
    entities = map_grounded_extractions([
        GroundedExtraction("location", "浙江省温州市", {
            "role": "pickup", "province": "浙江", "city": "温州", "full_address": "浙江省温州市", "action": "set"
        })
    ], "从浙江省温州市装货")
    assert entities[0].attributes["province"] == "浙江"


def test_mapper_rejects_invalid_location_province():
    with pytest.raises(StructuredIntentError, match="province"):
        map_grounded_extractions([GroundedExtraction("location", "温州", {
            "role": "pickup", "province": 123, "city": "温州", "action": "set"
        })], "从温州装货")


def test_mapper_rejects_location_full_address_outside_source():
    with pytest.raises(StructuredIntentError, match="full_address"):
        map_grounded_extractions(
            [
                GroundedExtraction(
                    "location",
                    "上海",
                    {
                        "role": "pickup",
                        "city": "上海",
                        "full_address": "上海浦东某仓库",
                        "action": "set",
                    },
                )
            ],
            "从上海装货",
        )


def test_empty_grounded_output_is_preserved_for_any_input():
    assert map_grounded_extractions([], "一吨苹果从温州到上海") == []
    assert map_grounded_extractions([], "你好") == []


def test_mapper_rejects_missing_or_invalid_llm_action_contract():
    with pytest.raises(StructuredIntentError, match="attributes.action"):
        map_grounded_extractions([GroundedExtraction("cargo", "苹果", {"name": "苹果"})])
    with pytest.raises(StructuredIntentError, match="attributes.action"):
        map_grounded_extractions([GroundedExtraction("cargo", "苹果", {"action": "unknown"})])


def test_injectable_backend_receives_context_and_maps_result():
    received = []

    def backend(text):
        received.append(text)
        return [GroundedExtraction("cargo", "一吨苹果", {"name": "苹果", "weight": "1吨", "action": "set"})]

    config = LLMConfig("key", "https://example.test/v1", "gpt-5.6-terra")
    entities = LangExtractEntityExtractor(config, backend=backend).extract(
        "一吨苹果", [{"role": "user", "content": "从温州到上海"}], "2026-08-17 10:00"
    )
    assert entities[0].attributes["action"] == "set"
    assert "【参考时间】2026-08-17 10:00" in received[0]
    assert "从温州到上海" not in received[0]


@pytest.mark.parametrize("mode", ["chat_completions", "responses"])
def test_langextract_provider_has_single_worker_finite_timeout_and_no_sdk_retry(monkeypatch, mode):
    import langextract as lx
    captured = {}

    def fake_extract(*args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(lx, "extract", fake_extract)
    extractor = LangExtractEntityExtractor(
        LLMConfig("key", "https://example.test/v1", "demo", timeout=3.5, api_mode=mode)
    )
    assert extractor.extract("苹果", "2026-08-17 10:00") == []
    assert captured["max_workers"] == 1
    assert captured["extraction_passes"] == 1
    provider = captured["model"]
    assert provider.max_workers == 1
    assert provider._client.max_retries == 0
    assert provider._client.timeout == 3.5


def test_reducer_prefers_mapped_action_attribute():
    updated = OrderContextReducer().apply(
        OrderContext(),
        [Entity("cargo", "add", {"name": "苹果", "weight": "1吨", "action": "set"}, "一吨苹果")],
    )
    assert updated.cargo == [{
        "name": "苹果",
        "weight": ["1吨"],
        "quantity": [],
        "volume": [],
        "dimensions": [],
    }]


def test_extract_backend_defaults_to_langextract_and_validates_values():
    env = {
        "LLM_API_KEY": "key",
        "LLM_BASE_URL": "https://example.test/v1",
        "LLM_MODEL": "gpt-5.6-terra",
    }
    assert load_config(env).extractor_backend == "langextract"
    assert load_config({**env, "EXTRACTOR_BACKEND": "json"}).extractor_backend == "json"
    with pytest.raises(ConfigurationError, match="EXTRACTOR_BACKEND"):
        load_config({**env, "EXTRACTOR_BACKEND": "other"})


def test_langextract_examples_cover_all_entity_classes_and_source_boundary():
    from langextract.core.tokenizer import UnicodeTokenizer
    from langextract.prompt_validation import validate_prompt_alignment
    from langextract.providers.schemas.openai import OpenAISchema

    examples = build_langextract_order_examples()
    assert validate_prompt_alignment(examples, tokenizer=UnicodeTokenizer()).issues == []

    schema = OpenAISchema.from_examples(examples).schema_dict
    variants = schema["properties"]["extractions"]["items"]["anyOf"]
    classes = {next(iter(item["properties"])) for item in variants}
    assert classes == {
        "time", "location", "person", "phone", "vehicle_type", "vehicle_specs",
        "cargo", "follow_car_number", "oneself_follow_flag", "invoice_type",
        "payment_type", "service_type", "remark",
    }
    assert "【待提取文本】一吨苹果" in format_langextract_source("一吨苹果", "2026-08-17 10:00")


def test_langextract_examples_align_chinese_entity_spans():
    from langextract.core.tokenizer import UnicodeTokenizer
    from langextract.prompt_validation import validate_prompt_alignment

    examples = build_langextract_order_examples()
    validation = validate_prompt_alignment(examples, tokenizer=UnicodeTokenizer())
    assert validation.issues == []

    rewrite_example = examples[1]
    assert [(item.extraction_text, item.extraction_class) for item in rewrite_example.extractions] == [
        ("一吨苹果", "cargo"),
        ("温州", "location"),
        ("上海", "location"),
    ]
    detailed = examples[2]
    assert detailed.extractions[0].attributes["full_address"] == "上海浦东金桥物流园3号仓库"
    assert detailed.extractions[1].attributes["full_address"] == "温州瓯海批发市场"


@pytest.mark.parametrize("text", ["苹果改成香蕉", "4米2冷链厢式车", "明天上午王强收货13800138000", "到付不开票快车", "苹果容易碎轻拿轻放", "你好"])
def test_prompt_contract_cases_accept_grounded_backend(text):
    assert isinstance(map_grounded_extractions([], text), list)


@pytest.mark.integration
def test_live_langextract_basic_order_probe():
    if os.getenv("INORDER_LLM_LIVE_TESTS") != "1":
        pytest.skip("set INORDER_LLM_LIVE_TESTS=1 to run the live LangExtract probe")
    entities = LangExtractEntityExtractor(load_config()).extract(
        "一吨苹果从温州到上海", [], "2026-08-17 10:00"
    )
    assert entities
    assert any(entity.type == "cargo" for entity in entities)
    roles = {entity.attributes.get("role") for entity in entities if entity.type == "location"}
    assert {"pickup", "dropoff"} <= roles
    vehicle = LangExtractEntityExtractor(load_config()).extract("4米2冷链厢式车", "2026-08-17 10:00")
    assert {entity.type for entity in vehicle} >= {"vehicle_type", "vehicle_specs"}
    remark = LangExtractEntityExtractor(load_config()).extract("苹果容易碎，轻拿轻放", "2026-08-17 10:00")
    assert any(entity.type == "remark" and entity.attributes.get("value") for entity in remark)
