from copy import deepcopy

import pytest

from inorder_llm.context import ContextReductionError, OrderContextReducer
from inorder_llm.context.models import HistoryConversation, OrderContext
from inorder_llm.extract.models import Entity
from inorder_llm.graph.order import build_order_processing_graph
from inorder_llm.intent.resolver import StructuredIntentError
from inorder_llm.rewrite.models import RewriteResult


class FakeRewriteModel:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def rewrite(self, message, history, order_context):
        self.calls.append((message, history, order_context))
        return self.result


class FakeExtractor:
    def __init__(self, entities=None, error=None):
        self.entities = list(entities or [])
        self.error = error
        self.calls = []

    def extract(self, message, reference_time):
        self.calls.append((message, reference_time))
        if self.error:
            raise self.error
        return self.entities


def _state(history=None, context=None):
    history = history or HistoryConversation()
    context = context or OrderContext()
    return {
        "message": "再加一吨苹果",
        "reference_time": "2026-08-17 10:00",
        "history": history,
        "order_context": context,
    }


def test_order_processing_graph_rewrites_then_extracts_incremental_text():
    history = HistoryConversation()
    history.append_user("当前订单已有一吨苹果")
    context = OrderContext(cargo=[{"name": "苹果", "weight": "1吨"}])
    rewrite = FakeRewriteModel(
        RewriteResult("已有一吨苹果，本轮再增加一吨苹果", "再加一吨苹果")
    )
    extractor = FakeExtractor(
        [Entity("cargo", "add", {"name": "苹果", "weight": "1吨"}, "一吨苹果")]
    )

    result = build_order_processing_graph(rewrite, extractor).invoke(
        _state(history, context)
    )

    assert result["rewrite_result"].extraction_text == "再加一吨苹果"
    assert result["entities"] == extractor.entities
    assert result["needs_clarification"] is False
    assert len(rewrite.calls) == 1
    assert len(extractor.calls) == 1
    assert extractor.calls[0][0] == "再加一吨苹果"
    assert extractor.calls[0][1] == "2026-08-17 10:00"


def test_clarification_route_skips_extractor_and_returns_empty_entities():
    rewrite = FakeRewriteModel(
        RewriteResult("", "", True, "历史中存在多个车型，无法确定目标")
    )
    extractor = FakeExtractor([Entity("vehicle_type", "set", {}, "4米2")])

    result = build_order_processing_graph(rewrite, extractor).invoke(_state())

    assert result["needs_clarification"] is True
    assert result["clarification_reason"] == "历史中存在多个车型，无法确定目标"
    assert result["entities"] == []
    assert extractor.calls == []


def test_graph_preserves_history_and_order_context():
    history = HistoryConversation()
    history.append_user("从上海发货")
    context = OrderContext(pickup_location={"city": "上海"})
    history_before = deepcopy(history.to_dict())
    context_before = deepcopy(context.to_dict())
    rewrite = FakeRewriteModel(RewriteResult("本轮新增一吨苹果", "再加一吨苹果"))
    extractor = FakeExtractor()

    build_order_processing_graph(rewrite, extractor).invoke(_state(history, context))

    assert history.to_dict() == history_before
    assert context.to_dict() == context_before


def test_rewrite_error_propagates_and_extractor_is_not_called():
    error = StructuredIntentError("invalid rewrite output")

    class FailingRewrite:
        def rewrite(self, message, history, order_context):
            raise error

    extractor = FakeExtractor()
    with pytest.raises(StructuredIntentError, match="invalid rewrite output"):
        build_order_processing_graph(FailingRewrite(), extractor).invoke(_state())
    assert extractor.calls == []


def test_extract_error_propagates_after_rewrite():
    rewrite = FakeRewriteModel(RewriteResult("本轮新增一吨苹果", "再加一吨苹果"))
    extractor = FakeExtractor(error=StructuredIntentError("invalid extraction output"))

    with pytest.raises(StructuredIntentError, match="invalid extraction output"):
        build_order_processing_graph(rewrite, extractor).invoke(_state())

    assert len(extractor.calls) == 1


def test_graph_applies_entities_to_new_order_context_without_mutating_input():
    original = OrderContext(cargo=[{"name": "苹果", "weight": "1吨"}])
    rewrite = FakeRewriteModel(RewriteResult("再加一吨香蕉", "再加一吨香蕉"))
    extractor = FakeExtractor(
        [Entity("cargo", "add", {"name": "香蕉", "weight": "1吨"}, "一吨香蕉")]
    )

    result = build_order_processing_graph(rewrite, extractor).invoke(_state(context=original))

    assert result["order_context"].cargo == [
        {"name": "苹果", "weight": "1吨"},
        {"name": "香蕉", "weight": "1吨"},
    ]
    assert result["order_context_updated"] is True
    assert original.cargo == [{"name": "苹果", "weight": "1吨"}]


def test_graph_supports_set_replace_and_remove_context_actions():
    reducer = OrderContextReducer()
    context = OrderContext()
    context = reducer.apply(context, [Entity("location", "set", {"role": "pickup", "city": "上海"})])
    context = reducer.apply(context, [Entity("location", "replace", {"role": "pickup", "city": "杭州"})])
    context = reducer.apply(context, [Entity("vehicle_specs", "set", {"extraction_text": "高顶"})])
    context = reducer.apply(context, [Entity("vehicle_specs", "remove", {"extraction_text": "高顶"})])
    context = reducer.apply(context, [Entity("location", "remove", {"role": "pickup"})])
    assert context.pickup_location is None
    assert context.vehicle_specs == []


def test_clarification_preserves_original_order_context():
    original = OrderContext(cargo=[{"name": "苹果", "weight": "1吨"}])
    rewrite = FakeRewriteModel(RewriteResult("", "", True, "车型不明确"))
    result = build_order_processing_graph(rewrite, FakeExtractor()).invoke(_state(context=original))
    assert result["order_context"] == original
    assert result["order_context_updated"] is False


def test_reducer_failure_does_not_return_partial_context():
    rewrite = FakeRewriteModel(RewriteResult("设置未知字段", "设置未知字段"))
    extractor = FakeExtractor([Entity("unsupported", "set", {"value": "x"}, "未知")])
    with pytest.raises(ContextReductionError):
        build_order_processing_graph(rewrite, extractor).invoke(_state())
