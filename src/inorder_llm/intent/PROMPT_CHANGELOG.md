# Prompt 变更记录

本文件记录 `inorder_llm` 中所有 LLM prompt 的变更、原因与评测结果。每次修改 prompt（当前为 `src/inorder_llm/intent/resolver.py` 中的 `MAIN_INTENT_SYSTEM_PROMPT` / `SUB_INTENT_SYSTEM_PROMPT`，或后续新增的 prompt）都应追加一条记录。

## 记录格式

每条记录包含以下字段：

| 字段 | 说明 |
| --- | --- |
| 日期 | 变更日期 (YYYY-MM-DD) |
| Prompt | 受影响的 prompt 常量名 |
| 变更摘要 | 改了什么（新旧差异要点） |
| 原因 | 为什么改（动机 / 触发场景） |
| 关联 | OpenSpec change / commit / PR |
| 评测结果 | 变更后的验证情况：单测通过情况、prompt 内容 / 消息角色断言、典型 case 表现、（如有）真实 LLM 评测集得分、回归情况 |

> 评测结果应尽量给出可复现的依据（命令、用例、得分），而不只是「通过」。

## 记录

### 2026-08-14

- **Prompt**: `MAIN_INTENT_SYSTEM_PROMPT`、`SUB_INTENT_SYSTEM_PROMPT`
- **变更摘要**:
  - 两个 prompt 由英文短字符串拼接改为中文完整结构化 prompt（定义、规则、边界示例、严格 JSON schema）。
  - 用户消息不再拼进 system 指令，改为作为独立 user message 发送（`_json_call` 发 system + user 两条 `ChatMessage`）。
  - 主意图 prompt 明确 `order`/`qa` 二分类与「执行优先」规则；子意图 prompt 明确多子意图、保守参数提取、`depends_on` 规则。
- **原因**: 主意图从 `order/qa/ambiguous` 三分类收敛为二分类，需要 prompt 明确「执行请求 vs 信息询问」边界；旧 prompt 把用户消息拼进 system 存在注入面且规则不清，输出不稳定。
- **关联**: OpenSpec change `simplify-intent-classification-and-prompts`（已归档至 `openspec/changes/archive/2026-08-14-simplify-intent-classification-and-prompts/`）
- **评测结果**:
  - `conda run -n agent python -m pytest -q` → 27 passed。
  - 新增 `tests/test_intent_resolver.py`：通过 prompt 内容断言（执行优先、操作方法、保守提取、JSON schema 关键词）与消息角色断言（system/user 顺序、user 内容=输入）。
  - 图路由测试 `tests/test_intent_graph.py` 通过（`order`→子意图、`qa`→跳过、`order` 无子意图→澄清）。
  - 尚无真实 LLM 评测集；分类准确率待后续建立评测集后补充。

### 2026-08-14（二）

- **Prompt**: `MAIN_INTENT_SYSTEM_PROMPT`、`SUB_INTENT_SYSTEM_PROMPT`
- **变更摘要**:
  - `MAIN_INTENT_SYSTEM_PROMPT` 的 `order` 锚点从「要求系统执行…操作」扩到「期望输出是行动/结果的业务目标意愿」，判据由命令动词转为期望输出类型。
  - 加入领域映射：运货/发货/配送/托运/下单 = `order` 业务目标词。
  - 加入咨询信号闸门词（了解/咨询/怎么/多少钱/能不能/一般），存在时即使提及业务目标也归 `qa`。
  - 边界示例新增：「我想从上海运货到温州」→ `order`、「运货到温州多少钱」→ `qa`、「上海到温州能运吗」→ `qa`。
  - `SUB_INTENT_SYSTEM_PROMPT` 的 `create_order` 加入「运货/发货/配送/托运等运输需求均映射为此子意图」领域映射。
- **原因**: 业务目标愿望陈述（如「我想从上海运货到温州」）因无命令动词被误判 `qa`，真实订单需求在主意图层丢失；语义偏窄，需扩到期望输出导向。
- **关联**: OpenSpec change `broaden-order-intent-to-business-goals`
- **评测结果**:
  - `conda run -n agent python -m pytest -q` → 29 passed。
  - `tests/test_intent_resolver.py`：新增断言 `期望的输出`、`运货`、`多少钱`。
  - `tests/test_intent_graph.py`：新增 `test_business_goal_message_routes_to_order`、`test_capability_inquiry_message_routes_to_qa`（基于 mock 意图识别器，验证消息透传与路由）。
  - 尚无真实 LLM 评测集；分类准确率待评测集补充。
