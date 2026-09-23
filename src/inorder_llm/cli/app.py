"""Interactive CLI for the full, intent, and order processing chains."""

from dataclasses import dataclass, field
from copy import deepcopy
import json
from typing import Callable, List, Optional

from ..context.models import HistoryConversation, OrderContext
from ..context.recovery import prepare_conversation_recovery
from ..context.summary import intent_view, to_data
from ..reference_time import resolve_context_reference_time
from .runners import ChainContext, FullChainRunner, IntentChainRunner, OrderChainRunner

CHAINS = ("full", "intent", "order")
# Kept as a public compatibility alias for callers of the previous CLI.
MODES = ("auto", "order", "qa", "plan")
HELP_TEXT = "命令：/chain [full|intent|order]、/intent、/mode、/context、/conversation、/clear、/help、/exit"


@dataclass
class CliSession:
    chain: str = "full"
    mode: str = "auto"  # compatibility display mode; chain is authoritative
    messages: List[str] = field(default_factory=list)
    history: HistoryConversation = field(default_factory=HistoryConversation)
    order_context: OrderContext = field(default_factory=OrderContext)
    # Resolved at the start of each message; never cached at session creation.
    reference_time: str = ""
    running: bool = True


class CommandParser:
    def parse(self, line: str):
        text = line.strip()
        if not text: return ("empty", None)
        if not text.startswith("/"): return ("message", text)
        parts = text.split()
        return (parts[0][1:].lower(), parts[1:] or None)


# Thin aliases: CLI shares dict conversion and intent unwrapping with the API
# path via context.summary (single source of truth).
_data = to_data
_intent_data = intent_view


def _vehicle_candidate_lines(result) -> List[str]:
    resolution = _data(result.get("vehicle_resolution"))
    if not isinstance(resolution, dict):
        return []
    lines = []
    labels = {
        "lower_bound_fit": "按范围下界通过",
        "upper_bound_only": "仅按范围上界通过，可能适配",
    }
    for index, candidate in enumerate(resolution.get("candidates", []), 1):
        level = labels.get(candidate.get("fit_level"), "适配等级未知")
        reason = candidate.get("reason") or ""
        slack = candidate.get("volume_slack_m3")
        detail = f"；体积余量 {slack}m³" if slack is not None else ""
        lines.append(
            f"候选车型{index}（{level}）：{candidate.get('vehicle_type')}"
            f"；{reason}{detail}"
        )
    return lines


def _assistant_summary(result, chain: str, mode: Optional[str] = None):
    """Build a compact history turn and metadata from structured results."""
    if isinstance(result, str):
        return result, {"chain": chain}
    if chain == "full":
        intent_result = result.get("intent_result", result)
        order_result = result.get("order_result")
        if order_result is not None:
            order_summary = _data(order_result.get("order_summary"))
            if isinstance(order_summary, dict):
                intent = _intent_data(intent_result).get("main_intent")
                status = order_summary.get("status", "incomplete")
                missing = order_summary.get("missing_required", [])
                text = order_summary.get("user_message") or order_summary.get("summary", "订单已解析")
                metadata = {"chain": "full", "main_intent": intent, "order_status": status}
                return text, metadata
            summary, metadata = _assistant_summary(order_result, "order")
            intent = _intent_data(intent_result).get("main_intent")
            metadata.update({"chain": "full", "main_intent": intent})
            return (f"主意图：{intent}；" + summary), metadata
        data = _intent_data(intent_result)
        intent = data.get("main_intent") if isinstance(data, dict) else None
        text = "主意图：" + str(intent or "未知")
        if result.get("qa_placeholder"):
            text += "；问答入口尚未实现"
        return text, {"chain": "full", "main_intent": intent}
    if chain == "order":
        order_summary = _data(result.get("order_summary"))
        if isinstance(order_summary, dict):
            text = order_summary.get("user_message") or order_summary.get("summary", "订单已解析")
            return text, {"chain": "order", "order_status": order_summary.get("status", "incomplete")}
        count = result.get("entity_count", len(result.get("entities", [])))
        updated = bool(result.get("order_context_updated"))
        return f"订单解析完成；Extract 提取 {count} 个实体；订单上下文" + ("已更新。" if updated else "未更新。"), {
            "chain": "order", "entity_count": count,
            "order_context_updated": updated,
        }
    data = _intent_data(result)
    intent = data.get("main_intent") if isinstance(data, dict) else None
    text = "已识别主意图：" + str(intent or "未知")
    return text + "。", {"chain": "intent", "main_intent": intent}


def format_result(result, chain: str = "intent", mode: Optional[str] = None) -> str:
    if isinstance(result, str): return result
    if chain == "qa": return "问答入口尚未实现（当前仅支持意图识别）。"
    if chain == "order":
        order_summary = _data(result.get("order_summary"))
        if isinstance(order_summary, dict):
            text = str(order_summary.get("user_message") or order_summary.get("summary", "订单已解析"))
            candidate_lines = _vehicle_candidate_lines(result)
            return "\n".join([text, *candidate_lines]) if candidate_lines else text
        rewrite = _data(result.get("rewrite_result"))
        lines = ["链路：order（仅解析，未执行业务）"]
        lines.append("订单处理：" + ("已进入" if result.get("order_graph_entered") else "未进入"))
        lines.append("Rewrite：" + ("已完成" if result.get("rewrite_completed") else "未完成"))
        if rewrite: lines.append("Rewrite：" + str(rewrite.get("rewritten_text", "")))
        lines.append("Extract：" + ("已执行" if result.get("extract_executed") else "未执行"))
        lines.append("实体数量：" + str(result.get("entity_count", len(result.get("entities", [])))))
        lines.append("订单上下文：" + ("已更新" if result.get("order_context_updated") else "未更新"))
        if result.get("cargo_profile_updated"):
            lines.append("货物画像：已重建")
        resolution = _data(result.get("vehicle_resolution"))
        if resolution:
            lines.append("车型：" + str(resolution.get("vehicle_type", "")))
            if resolution.get("vehicle_specs"):
                lines.append("车型规格：" + "、".join(resolution["vehicle_specs"]))
            lines.append("车型来源：" + str(resolution.get("source", "")))
            if resolution.get("reason"):
                lines.append("车型原因：" + str(resolution["reason"]))
            lines.extend(_vehicle_candidate_lines(result))
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
    data = _data(result)
    if not isinstance(data, dict): return "未生成意图识别结果。"
    if mode == "plan": return json.dumps(data, ensure_ascii=False, indent=2)
    lines = ["链路：intent（仅识别，未执行业务）", "主意图：" + str(data.get("main_intent"))]
    return "\n".join(lines)


class IntentCli:
    def __init__(self, graph=None, intent_graph=None, order_graph=None, full_runner=None, main_graph=None,
                 input_fn: Callable[[str], str] = input, output_fn: Callable[[str], None] = print):
        self.input, self.output = input_fn, output_fn
        self.session, self.parser = CliSession(), CommandParser()
        if intent_graph is None: intent_graph = graph
        self.intent_runner = IntentChainRunner(intent_graph) if intent_graph is not None else None
        self.order_runner = OrderChainRunner(order_graph) if order_graph is not None else None
        self.full_runner = full_runner or (FullChainRunner(self.intent_runner, self.order_runner, main_graph=main_graph) if self.intent_runner else None)

    def run_with_main_graph(self, main_graph):
        self.full_runner = FullChainRunner(self.intent_runner, self.order_runner, main_graph=main_graph)
        return self.run()

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
        if command == "context":
            return json.dumps(self.session.order_context.to_dict(), ensure_ascii=False, indent=2)
        if command == "conversation":
            return json.dumps(self.session.history.to_dict(), ensure_ascii=False, indent=2)
        if command == "clear":
            chain = self.session.chain
            self.session.messages.clear(); self.session.history = HistoryConversation(); self.session.order_context = OrderContext()
            return "会话已清空。当前链路：" + chain
        if command in ("exit", "quit"): self.session.running = False; return "再见。"
        return "未知命令：/" + command + "。输入 /help 查看帮助。"

    def handle_message(self, message):
        self.session.messages.append(message)
        self.session.reference_time = resolve_context_reference_time(
            self.session.order_context.reference_time
        )
        self.session.order_context.reference_time = self.session.reference_time
        if self.session.mode == "qa": return format_result(None, "qa")
        original_history = self.session.history
        recovery = prepare_conversation_recovery(original_history, message)
        working_history = recovery.history
        working_history.append_user(recovery.message)
        # Persist the user turn before invoking the graph. If the request
        # fails, this deliberately remains a pending turn for the next retry.
        self.session.history = working_history
        context = ChainContext(working_history, self.session.order_context, self.session.reference_time)
        runner = {"full": self.full_runner, "intent": self.intent_runner, "order": self.order_runner}[self.session.chain]
        if runner is None: return "当前链路未配置，无法识别。"
        result = runner.run(recovery.message, context)
        if self.session.chain == "order":
            updated_context = result.get("order_context")
            if updated_context is not None:
                if not updated_context.reference_time:
                    updated_context = deepcopy(updated_context)
                    updated_context.reference_time = self.session.reference_time
                self.session.order_context = updated_context
        elif self.session.chain == "full":
            order_result = result.get("order_result")
            if order_result and order_result.get("order_context") is not None:
                updated_context = order_result["order_context"]
                if not updated_context.reference_time:
                    updated_context = deepcopy(updated_context)
                    updated_context.reference_time = self.session.reference_time
                self.session.order_context = updated_context
        output = format_result(result, self.session.chain, self.session.mode)
        summary, metadata = _assistant_summary(result, self.session.chain, self.session.mode)
        working_history.append_assistant(summary, metadata)
        self.session.history = working_history
        return output

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
