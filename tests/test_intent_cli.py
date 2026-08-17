from inorder_llm.cli.app import CHAINS, CliSession, CommandParser, IntentCli, MODES
from inorder_llm.context.models import HistoryConversation, OrderContext
from inorder_llm.rewrite.models import RewriteResult


class FakeGraph:
    def __init__(self):
        self.calls = []

    def invoke(self, state):
        self.calls.append(state)
        return {"intent_plan": {"main_intent": "order", "sub_intents": [{"name": "create_order"}], "needs_clarification": False}}


def test_parser_commands_and_messages():
    parser = CommandParser()
    assert parser.parse("/intent order") == ("intent", ["order"])
    assert parser.parse("hello") == ("message", "hello")
    assert parser.parse("   ") == ("empty", None)


def test_mode_switch_help_clear_and_exit():
    outputs = []
    cli = IntentCli(output_fn=outputs.append)
    assert cli.switch_mode("plan") == "当前模式：plan"
    assert cli.session.mode == "plan"
    assert cli.handle_command("mode") == "当前模式：plan"
    cli.session.messages.append("x")
    assert "清空" in cli.handle_command("clear")
    assert cli.session.messages == []
    assert "非法模式" in cli.handle_command("intent", ["bad"])
    assert cli.handle_command("exit") == "再见。"
    assert not cli.session.running


def test_messages_route_to_graph_and_plan_formats():
    graph = FakeGraph()
    cli = IntentCli(graph=graph)
    output = cli.handle_message("我要下单")
    assert "create_order" in output
    assert graph.calls == [{"message": "我要下单"}]


def test_qa_mode_is_placeholder_without_graph_call():
    graph = FakeGraph()
    cli = IntentCli(graph=graph)
    cli.switch_mode("qa")
    assert "尚未实现" in cli.handle_message("物流规则")
    assert not graph.calls


def test_scripted_session_supports_intent_and_exit():
    graph = FakeGraph()
    lines = iter(["/intent", "plan", "测试意图", "/exit"])
    outputs = []
    cli = IntentCli(graph=graph, input_fn=lambda _: next(lines), output_fn=outputs.append)
    cli.run()
    assert cli.session.mode == "plan"
    assert any("create_order" in item for item in outputs)


class FakeIntentGraph:
    def __init__(self, main="order"):
        self.main = main
        self.calls = []

    def invoke(self, state):
        self.calls.append(state)
        return {
            "main_intent": self.main,
            "intent_plan": {
                "main_intent": self.main,
                "sub_intents": [{"name": "create_order"}] if self.main == "order" else [],
                "needs_clarification": False,
            },
        }


class FakeOrderGraph:
    def __init__(self, clarification=False):
        self.calls = []
        self.clarification = clarification

    def invoke(self, state):
        self.calls.append(state)
        if self.clarification:
            return {
                "rewrite_result": RewriteResult("", "", True, "车型指代不唯一"),
                "entities": [],
                "needs_clarification": True,
                "clarification_reason": "车型指代不唯一",
            }
        return {
            "rewrite_result": RewriteResult("本轮新增一吨苹果", "再加一吨苹果"),
            "entities": [],
            "needs_clarification": False,
        }


def test_chain_switches_and_routes_intent_order_and_full():
    intent = FakeIntentGraph("order")
    order = FakeOrderGraph()
    cli = IntentCli(intent_graph=intent, order_graph=order)
    assert cli.session.chain == "full"
    assert cli.handle_command("chain", ["intent"]) == "当前链路：intent"
    cli.handle_message("识别一下")
    assert len(intent.calls) == 1
    assert order.calls == []

    assert cli.handle_command("chain", ["order"]) == "当前链路：order"
    cli.handle_message("再加一吨苹果")
    assert len(order.calls) == 1
    assert order.calls[0]["history"].turns
    assert isinstance(order.calls[0]["order_context"], OrderContext)
    assert order.calls[0]["reference_time"]

    assert cli.handle_command("chain", ["full"]) == "当前链路：full"
    cli.handle_message("完整执行")
    assert len(intent.calls) == 2
    assert len(order.calls) == 2


def test_full_qa_skips_order_graph_and_legacy_intent_is_alias():
    intent = FakeIntentGraph("qa")
    order = FakeOrderGraph()
    cli = IntentCli(intent_graph=intent, order_graph=order)
    assert cli.handle_command("intent") == "当前链路：intent"
    assert cli.handle_command("chain", ["full"]) == "当前链路：full"
    output = cli.handle_message("上海能运吗")
    assert "问答入口尚未实现" in output
    assert order.calls == []


def test_full_output_reports_extract_execution_and_entity_count():
    intent = FakeIntentGraph("order")
    order = FakeOrderGraph()
    cli = IntentCli(intent_graph=intent, order_graph=order)
    output = cli.handle_message("再加一吨苹果")
    assert "订单处理：已进入" in output
    assert "Rewrite：已完成" in output
    assert "澄清：否" in output
    assert "Extract：已执行" in output
    assert "实体数量：0" in output


def test_full_output_reports_clarification_and_extract_skip():
    intent = FakeIntentGraph("order")
    order = FakeOrderGraph(clarification=True)
    cli = IntentCli(intent_graph=intent, order_graph=order)
    output = cli.handle_message("换回之前那个车")
    assert "订单处理：已进入" in output
    assert "Rewrite：已完成" in output
    assert "澄清：是" in output
    assert "Extract：已跳过" in output
    assert "车型指代不唯一" in output


def test_order_chain_persists_updated_context_between_messages():
    class ContextGraph:
        def invoke(self, state):
            updated = OrderContext(cargo=[{"name": "苹果", "weight": "1吨"}])
            return {
                "rewrite_result": RewriteResult("已提取", state["message"]),
                "entities": [],
                "order_context": updated,
                "order_context_updated": True,
                "needs_clarification": False,
            }

    cli = IntentCli(order_graph=ContextGraph())
    cli.switch_chain("order")
    cli.handle_message("一吨苹果")
    assert cli.session.order_context.cargo == [{"name": "苹果", "weight": "1吨"}]
    output = cli.handle_message("继续")
    assert "订单上下文：已更新" in output


def test_clear_resets_history_and_order_context_but_keeps_chain():
    cli = IntentCli(intent_graph=FakeIntentGraph())
    cli.switch_chain("order")
    cli.session.messages.append("x")
    cli.session.history.append_user("历史")
    cli.session.order_context = OrderContext(vehicle_type="truck_4m2")
    assert "当前链路：order" in cli.handle_command("clear")
    assert cli.session.chain == "order"
    assert cli.session.messages == []
    assert cli.session.history.turns == []
    assert cli.session.order_context == OrderContext()


def test_chain_constants_are_explicit():
    assert CHAINS == ("full", "intent", "order")
