"""Interactive CLI for the full, intent, and order processing chains."""

from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Callable, List, Optional
from zoneinfo import ZoneInfo

from ..context.models import HistoryConversation, OrderContext
from .runners import ChainContext, FullChainRunner, IntentChainRunner, OrderChainRunner

CHAINS = ("full", "intent", "order")
# Kept as a public compatibility alias for callers of the previous CLI.
MODES = ("auto", "order", "qa", "plan")
HELP_TEXT = "命令：/chain [full|intent|order]、/intent、/mode、/clear、/help、/exit"


def _reference_time() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M")


@dataclass
class CliSession:
    chain: str = "full"
    mode: str = "auto"  # compatibility display mode; chain is authoritative
    messages: List[str] = field(default_factory=list)
    history: HistoryConversation = field(default_factory=HistoryConversation)
    order_context: OrderContext = field(default_factory=OrderContext)
    reference_time: str = field(default_factory=_reference_time)
    running: bool = True


class CommandParser:
    def parse(self, line: str):
        text = line.strip()
        if not text: return ("empty", None)
        if not text.startswith("/"): return ("message", text)
        parts = text.split()
        return (parts[0][1:].lower(), parts[1:] or None)


def _data(value):
    return value.to_dict() if hasattr(value, "to_dict") else value


def format_result(result, chain: str = "intent", mode: Optional[str] = None) -> str:
    if isinstance(result, str): return result
    if chain == "qa": return "问答入口尚未实现（当前仅支持意图识别）。"
    if chain == "order":
        rewrite = _data(result.get("rewrite_result"))
        lines = ["链路：order（仅解析，未执行业务）"]
        lines.append("订单处理：" + ("已进入" if result.get("order_graph_entered") else "未进入"))
        lines.append("Rewrite：" + ("已完成" if result.get("rewrite_completed") else "未完成"))
        if rewrite: lines.append("Rewrite：" + str(rewrite.get("rewritten_text", "")))
        if result.get("needs_clarification"):
            lines.append("澄清：是")
            lines.append("Extract：已跳过")
            lines.append("原因：" + str(result.get("extract_skipped_reason") or result.get("clarification_reason") or "未提供原因"))
        else:
            lines.append("澄清：否")
            lines.append("Extract：" + ("已执行" if result.get("extract_executed") else "未执行"))
        lines.append("实体数量：" + str(result.get("entity_count", len(result.get("entities", [])))))
        lines.append("订单上下文：" + ("已更新" if result.get("order_context_updated") else "未更新"))
        for entity in result.get("entities", []):
            item = _data(entity)
            lines.append("Entity：" + json.dumps(item, ensure_ascii=False))
        return "\n".join(lines)
    if chain == "full":
        intent_result = result.get("intent_result", result)
        text = ["链路：full"]
        text.append(format_result(intent_result, "intent", mode))
        if result.get("order_result"):
            text.append(format_result(result["order_result"], "order"))
        elif result.get("order_graph_entered") is False:
            text.append("订单处理：未进入\nExtract：未执行\n原因：" + str(result.get("extract_skipped_reason") or "未提供原因"))
        elif result.get("qa_placeholder"):
            text.append(result["qa_placeholder"])
        return "\n".join(text)
    plan = result.get("intent_plan") if isinstance(result, dict) else getattr(result, "intent_plan", result)
    if plan is None: return "未生成意图计划。"
    data = _data(plan)
    if mode == "plan": return json.dumps(data, ensure_ascii=False, indent=2)
    lines = ["链路：intent（仅识别，未执行业务）", "主意图：" + str(data.get("main_intent"))]
    if data.get("sub_intents"):
        lines.append("子意图：")
        for step in data["sub_intents"]:
            item = _data(step)
            lines.append("  - " + item["name"])
            if item.get("depends_on"): lines.append("    依赖：" + ", ".join(item["depends_on"]))
    if data.get("needs_clarification"): lines.append("需要澄清：" + str(data.get("clarification_reason") or "未提供原因"))
    return "\n".join(lines)


class IntentCli:
    def __init__(self, graph=None, intent_graph=None, order_graph=None, full_runner=None,
                 input_fn: Callable[[str], str] = input, output_fn: Callable[[str], None] = print):
        self.input, self.output = input_fn, output_fn
        self.session, self.parser = CliSession(), CommandParser()
        if intent_graph is None: intent_graph = graph
        self.intent_runner = IntentChainRunner(intent_graph) if intent_graph is not None else None
        self.order_runner = OrderChainRunner(order_graph) if order_graph is not None else None
        self.full_runner = full_runner or (FullChainRunner(self.intent_runner, self.order_runner) if self.intent_runner else None)

    def switch_chain(self, chain):
        if chain not in CHAINS: return "非法链路，可选：" + ", ".join(CHAINS)
        self.session.chain = chain
        self.session.mode = {"full": "auto", "intent": "plan", "order": "order"}[chain]
        return "当前链路：" + chain

    def switch_mode(self, mode):
        if mode in CHAINS: return self.switch_chain(mode)
        if mode not in MODES: return "非法模式，可选：" + ", ".join(MODES)
        self.session.mode = mode
        if mode == "qa": return "当前模式：qa（暂未实现真实问答）"
        if mode == "plan": self.session.chain = "intent"; return "当前模式：plan"
        if mode == "order": self.session.chain = "order"; return "当前模式：order"
        self.session.chain = "full"; return "当前模式：auto"

    def handle_command(self, command, args=None):
        args = list(args or [])
        if command == "chain":
            return self.switch_chain(args[0].lower()) if args else "请选择链路：" + ", ".join(CHAINS)
        if command == "intent":
            return self.switch_chain("intent") if not args else self.switch_mode(args[0].lower())
        if command == "mode":
            if self.session.mode in MODES and self.session.mode != "auto":
                return "当前模式：" + self.session.mode
            return "当前链路：" + self.session.chain
        if command == "help": return HELP_TEXT
        if command == "clear":
            chain = self.session.chain
            self.session.messages.clear(); self.session.history = HistoryConversation(); self.session.order_context = OrderContext()
            return "会话已清空。当前链路：" + chain
        if command in ("exit", "quit"): self.session.running = False; return "再见。"
        return "未知命令：/" + command + "。输入 /help 查看帮助。"

    def handle_message(self, message):
        self.session.messages.append(message)
        if self.session.mode == "qa": return format_result(None, "qa")
        self.session.history.append_user(message)
        context = ChainContext(self.session.history, self.session.order_context, self.session.reference_time)
        runner = {"full": self.full_runner, "intent": self.intent_runner, "order": self.order_runner}[self.session.chain]
        if runner is None: return "当前链路未配置，无法识别。"
        result = runner.run(message, context)
        if self.session.chain == "order":
            updated_context = result.get("order_context")
            if updated_context is not None:
                self.session.order_context = updated_context
        elif self.session.chain == "full":
            order_result = result.get("order_result")
            if order_result and order_result.get("order_context") is not None:
                self.session.order_context = order_result["order_context"]
        return format_result(result, self.session.chain, self.session.mode)

    def run(self):
        self.output("InOrder[" + self.session.chain + "] 输入 /help 查看命令。")
        while self.session.running:
            try: line = self.input("InOrder[" + self.session.chain + "]> ")
            except (EOFError, KeyboardInterrupt): self.session.running = False; self.output("再见。"); break
            kind, value = self.parser.parse(line)
            if kind == "empty": continue
            if kind == "message": output = self.handle_message(value)
            elif kind in ("chain", "intent") and not value:
                self.output("请选择链路（" + ", ".join(CHAINS) + "）：")
                try:
                    choice = self.input("chain> ").strip().lower()
                    output = self.switch_mode(choice) if kind == "intent" else self.switch_chain(choice)
                except (EOFError, KeyboardInterrupt): self.session.running = False; self.output("再见。"); break
            else: output = self.handle_command(kind, value)
            if output: self.output(output)
