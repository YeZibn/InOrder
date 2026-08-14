"""Interactive, recognition-only CLI for the intent graph."""

from dataclasses import dataclass, field
import json
from typing import Callable, Iterable, List, Optional, Sequence, TextIO

MODES = ("auto", "order", "qa", "plan")
HELP_TEXT = "命令：/intent [auto|order|qa|plan]、/mode、/help、/clear、/exit"


@dataclass
class CliSession:
    mode: str = "auto"
    messages: List[str] = field(default_factory=list)
    running: bool = True


class CommandParser:
    def parse(self, line: str):
        text = line.strip()
        if not text:
            return ("empty", None)
        if not text.startswith("/"):
            return ("message", text)
        parts = text.split()
        return (parts[0][1:].lower(), parts[1:] or None)


def format_result(result, mode: str) -> str:
    if isinstance(result, str):
        return result
    if mode == "qa":
        return "问答入口尚未实现（当前仅支持意图识别）。"
    plan = result.get("intent_plan") if isinstance(result, dict) else getattr(result, "intent_plan", result)
    if plan is None:
        return "未生成意图计划。"
    data = plan.to_dict() if hasattr(plan, "to_dict") else plan
    if mode == "plan":
        return json.dumps(data, ensure_ascii=False, indent=2)
    lines = ["识别-only：未执行业务", "主意图：" + str(data.get("main_intent"))]
    steps = data.get("sub_intents", [])
    if steps:
        lines.append("子意图：")
        for step in steps:
            lines.append("  - " + step["name"])
            if step.get("depends_on"):
                lines.append("    依赖：" + ", ".join(step["depends_on"]))
    if data.get("needs_clarification"):
        lines.append("需要澄清：" + str(data.get("clarification_reason") or "未提供原因"))
    return "\n".join(lines)


class IntentCli:
    def __init__(self, graph=None, input_fn: Callable[[str], str] = input, output_fn: Callable[[str], None] = print):
        self.graph = graph
        self.input = input_fn
        self.output = output_fn
        self.session = CliSession()
        self.parser = CommandParser()

    def switch_mode(self, mode: str) -> str:
        if mode not in MODES:
            return "非法模式，可选：" + ", ".join(MODES)
        self.session.mode = mode
        return "当前模式：" + mode

    def handle_command(self, command: str, args: Optional[Sequence[str]] = None) -> Optional[str]:
        args = list(args or [])
        if command == "intent":
            if args:
                return self.switch_mode(args[0].lower())
            return "请选择模式：" + ", ".join(MODES) + "（可再次输入 /intent <mode> 切换）"
        if command == "mode":
            return "当前模式：" + self.session.mode
        if command == "help":
            return HELP_TEXT
        if command == "clear":
            self.session.messages.clear()
            return "会话已清空。当前模式：" + self.session.mode
        if command in ("exit", "quit"):
            self.session.running = False
            return "再见。"
        return "未知命令：/" + command + "。输入 /help 查看帮助。"

    def handle_message(self, message: str) -> str:
        self.session.messages.append(message)
        if self.session.mode == "qa":
            return format_result(None, "qa")
        if self.graph is None:
            return "意图图未配置，无法识别。"
        result = self.graph.invoke({"message": message})
        return format_result(result, self.session.mode)

    def run(self) -> None:
        self.output("InOrder[" + self.session.mode + "] 输入 /help 查看命令。")
        while self.session.running:
            try:
                line = self.input("InOrder[" + self.session.mode + "]> ")
            except (EOFError, KeyboardInterrupt):
                self.session.running = False
                self.output("再见。")
                break
            kind, value = self.parser.parse(line)
            if kind == "empty":
                continue
            if kind == "message":
                output = self.handle_message(value)
            elif kind == "intent" and not value:
                self.output("请选择模式（" + ", ".join(MODES) + "）：")
                try:
                    selected = self.input("mode> ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    self.session.running = False
                    self.output("再见。")
                    break
                output = self.switch_mode(selected)
            else:
                output = self.handle_command(kind, value)
            if output:
                self.output(output)


def main(argv=None):
    from .intent_graph import build_intent_graph
    from .intent_planning import LLMIntentModel
    from .client import LLMClient
    from .config import load_config

    graph = build_intent_graph(LLMIntentModel(LLMClient(load_config())))
    IntentCli(graph=graph).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
