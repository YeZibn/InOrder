from inorder_llm.intent_cli import CliSession, CommandParser, IntentCli, MODES


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
