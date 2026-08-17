"""LangExtract adapter and grounded-to-business entity mapping."""

from typing import Any, Callable, Iterable, List, Mapping, Optional, Sequence

from ..infrastructure.llm import LLMConfig
from ..intent.resolver import StructuredIntentError
from .models import Entity, GroundedExtraction


LANGEXTRACT_ORDER_PROMPT_DESCRIPTION = (
    "从物流订单文本中提取原文可定位的 cargo、location、vehicle_type、vehicle_specs、time、phone 和 remark。"
    "每条提取必须对应原文片段；attributes 中包含业务字段和 action(add/set/remove/replace)。"
    "从A到B时第一个地址为pickup，第二个为dropoff。未识别到实体时返回空提取。"
)

_VALID_ACTIONS = ("add", "set", "remove", "replace")


def _entity_from_grounded(item: GroundedExtraction) -> Entity:
    if not isinstance(item.extraction_class, str) or not item.extraction_class:
        raise StructuredIntentError("grounded extraction requires extraction_class")
    if not isinstance(item.extraction_text, str) or not item.extraction_text:
        raise StructuredIntentError("grounded extraction requires extraction_text")
    if not isinstance(item.attributes, Mapping):
        raise StructuredIntentError("grounded extraction attributes must be a mapping")
    attrs = dict(item.attributes)
    action = attrs.get("action")
    if action not in _VALID_ACTIONS:
        raise StructuredIntentError("grounded extraction requires attributes.action: add, set, remove, or replace")
    return Entity(item.extraction_class, action, attrs, item.extraction_text)


def map_grounded_extractions(
    extractions: Iterable[GroundedExtraction], _source_text: Optional[str] = None
) -> List[Entity]:
    """Copy LLM-decided grounded entities into the reducer-compatible model."""
    entities: List[Entity] = []
    for item in extractions:
        entities.append(_entity_from_grounded(item))
    return entities


def _to_grounded(raw: Any) -> GroundedExtraction:
    attrs = getattr(raw, "attributes", None) or {}
    interval = getattr(raw, "char_interval", None)
    metadata = {
        "char_start": getattr(interval, "start_pos", None) if interval else None,
        "char_end": getattr(interval, "end_pos", None) if interval else None,
        "alignment_status": str(getattr(getattr(raw, "alignment_status", None), "value", "")) or None,
    }
    return GroundedExtraction(getattr(raw, "extraction_class"), getattr(raw, "extraction_text"), attrs, metadata)


class LangExtractEntityExtractor:
    """Production extractor backed by LangExtract's OpenAI-compatible provider."""

    def __init__(self, config: LLMConfig, backend: Optional[Callable[..., Any]] = None):
        self.config = config
        self.backend = backend

    def _call_backend(self, text: str):
        if self.backend is not None:
            return self.backend(text)
        try:
            import langextract as lx
            from langextract.data import ExampleData, Extraction
        except ImportError as exc:
            raise StructuredIntentError("langextract is not installed") from exc
        examples = [
            ExampleData(
                text="我要两吨苹果从上海运到温州",
                extractions=[
                    Extraction("cargo", "两吨苹果", attributes={"name": "苹果", "weight": "2吨", "action": "set"}),
                    Extraction("location", "上海", attributes={"role": "pickup", "city": "上海", "action": "set"}),
                    Extraction("location", "温州", attributes={"role": "dropoff", "city": "温州", "action": "set"}),
                ],
            ),
            ExampleData(
                text="再加一吨苹果",
                extractions=[Extraction("cargo", "一吨苹果", attributes={"name": "苹果", "weight": "1吨", "action": "add"})],
            ),
        ]
        return lx.extract(
            text,
            prompt_description=LANGEXTRACT_ORDER_PROMPT_DESCRIPTION,
            examples=examples,
            model_id=self.config.model,
            api_key=self.config.api_key,
            model_url=self.config.base_url,
            language_model_params={"reasoning_effort": self.config.reasoning_effort} if self.config.reasoning_effort else None,
            extraction_passes=1,
        )

    def extract(self, message: str, history: Sequence[Mapping[str, str]], reference_time: str) -> List[Entity]:
        history_text = "\n".join(f"{m.get('role', '')}: {m.get('content', '')}" for m in history)
        history_block = f"【对话历史】\n{history_text}\n" if history_text else ""
        source = f"【参考时间】{reference_time}\n{history_block}{message}"
        result = self._call_backend(source)
        raw_items = getattr(result, "extractions", None) if not isinstance(result, list) else result
        grounded = [_to_grounded(item) if not isinstance(item, GroundedExtraction) else item for item in (raw_items or [])]
        return map_grounded_extractions(grounded, message)


__all__ = [
    "LANGEXTRACT_ORDER_PROMPT_DESCRIPTION",
    "LangExtractEntityExtractor",
    "map_grounded_extractions",
]
