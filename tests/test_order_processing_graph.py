from copy import deepcopy

import pytest

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

    def extract(self, message, history, reference_time):
        self.calls.append((message, history, reference_time))
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
    assert extractor.calls[0][1] == history.as_llm_messages()
    assert extractor.calls[0][2] == "2026-08-17 10:00"


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
