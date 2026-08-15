# Prompt 变更记录

本文件记录 `inorder_llm` 中所有 LLM prompt 的变更、原因与评测结果。按 **prompt 常量** 分层组织，每个 prompt 下按日期排列变更，以体现渐进式进化。当前覆盖 `intent/resolver.py`（`MAIN_INTENT_SYSTEM_PROMPT` / `SUB_INTENT_SYSTEM_PROMPT`）与 `extract/resolver.py`（`EXTRACTION_SYSTEM_PROMPT`）；后续新增的 prompt 常量同样在此记录。

## 记录格式

每个 prompt 常量为一个 `###` 标题（标注所在文件），其下按日期（`####`）追加变更记录。每条记录包含以下字段：

| 字段 | 说明 |
| --- | --- |
| 日期 | 变更日期 (YYYY-MM-DD)，以系统真实日期为准（运行 `date "+%Y-%m-%d %A"` 确认） |
| 变更摘要 | 改了什么（新旧差异要点），聚焦本 prompt 的具体变化 |
| 原因 | 为什么改（动机 / 触发场景） |
| 关联 | OpenSpec change / commit / PR |
| 评测结果 | 变更后的验证情况：单测通过情况、prompt 内容 / 消息角色断言、典型 case 表现、（如有）真实 LLM 评测集得分、回归情况 |

> 评测结果应尽量给出可复现的依据（命令、用例、得分），而不只是「通过」。

## 记录

### `MAIN_INTENT_SYSTEM_PROMPT`（`intent/resolver.py`）

#### 2026-08-14

- **变更摘要**:
  - prompt 由英文短字符串拼接改为中文完整结构化 prompt（定义、规则、边界示例、严格 JSON schema）。
  - 用户消息不再拼进 system 指令，改为作为独立 user message 发送（`_json_call` 发 system + user 两条 `ChatMessage`）。
  - 明确 `order`/`qa` 二分类与「执行优先」规则（同时包含信息询问和执行请求时归 order）。
- **原因**: 主意图从 `order/qa/ambiguous` 三分类收敛为二分类，需要 prompt 明确「执行请求 vs 信息询问」边界；旧 prompt 把用户消息拼进 system 存在注入面且规则不清，输出不稳定。
- **关联**: OpenSpec change `simplify-intent-classification-and-prompts`（已归档至 `openspec/changes/archive/2026-08-14-simplify-intent-classification-and-prompts/`）
- **评测结果**:
  - `conda run -n agent python -m pytest -q` → 27 passed。
  - `tests/test_intent_resolver.py`：prompt 内容断言（执行优先、JSON schema 关键词）与消息角色断言（system/user 顺序、user 内容=输入）。
  - 图路由测试 `tests/test_intent_graph.py` 通过（`order`→子意图、`qa`→跳过、`order` 无子意图→澄清）。
  - 尚无真实 LLM 评测集；分类准确率待后续建立评测集后补充。

#### 2026-08-15

- **变更摘要**:
  - `order` 锚点从「要求系统执行…操作」扩到「期望输出是行动/结果的业务目标意愿」，判据由命令动词转为期望输出类型。
  - 加入领域映射：运货/发货/配送/托运/下单 = `order` 业务目标词。
  - 加入咨询信号闸门词（了解/咨询/怎么/多少钱/能不能/一般），存在时即使提及业务目标也归 `qa`。
  - 边界示例新增：「我想从上海运货到温州」→ `order`、「运货到温州多少钱」→ `qa`、「上海到温州能运吗」→ `qa`。
- **原因**: 业务目标愿望陈述（如「我想从上海运货到温州」）因无命令动词被误判 `qa`，真实订单需求在主意图层丢失；语义偏窄，需扩到期望输出导向。
- **关联**: OpenSpec change `broaden-order-intent-to-business-goals`（已归档）
- **评测结果**:
  - `conda run -n agent python -m pytest -q` → 29 passed。
  - `tests/test_intent_resolver.py`：新增断言 `期望的输出`、`运货`、`多少钱`。
  - `tests/test_intent_graph.py`：新增 `test_business_goal_message_routes_to_order`、`test_capability_inquiry_message_routes_to_qa`。
  - 尚无真实 LLM 评测集；分类准确率待评测集补充。

---

### `SUB_INTENT_SYSTEM_PROMPT`（`intent/resolver.py`）

#### 2026-08-14

- **变更摘要**:
  - prompt 由英文短字符串拼接改为中文完整结构化 prompt（定义、规则、边界示例、严格 JSON schema）。
  - 用户消息不再拼进 system 指令，改为作为独立 user message 发送。
  - 明确多子意图提取、保守参数提取（仅含用户明确表述的字段）、`depends_on` 依赖规则。
- **原因**: 子意图需要明确多子意图提取、保守参数提取、`depends_on` 依赖规则；旧 prompt 规则不清导致参数臆造与依赖混乱。
- **关联**: OpenSpec change `simplify-intent-classification-and-prompts`（已归档）
- **评测结果**:
  - `conda run -n agent python -m pytest -q` → 27 passed。
  - `tests/test_intent_resolver.py`：prompt 内容断言（保守提取、`depends_on`、JSON schema 关键词）。
  - 图路由测试 `tests/test_intent_graph.py` 通过。
  - 尚无真实 LLM 评测集。

#### 2026-08-15

- **变更摘要**:
  - `create_order` 加入「运货/发货/配送/托运等运输需求均映射为此子意图」领域映射。
- **原因**: 主意图已将业务目标词（运货/发货等）纳入 `order`，子意图层需同步覆盖，避免主意图判 `order` 但子意图无法匹配 `create_order`。
- **关联**: OpenSpec change `broaden-order-intent-to-business-goals`（已归档）
- **评测结果**:
  - `conda run -n agent python -m pytest -q` → 29 passed。
  - 无新增 SUB 专属断言（本次改动为单行领域映射补充，回归通过即可）。
  - 尚无真实 LLM 评测集。

---

### `EXTRACTION_SYSTEM_PROMPT`（`extract/resolver.py`）

#### 2026-08-15

- **变更摘要**:
  - 新增 `extract` 模块（`models`/`resolver`），引入实体提取 prompt。
  - 保留现成 14 类实体定义与全部语义归一规则（时间归一、车型归一、地址角色、人名拆分、history context 标记）。
  - 扩展 action 维度：每个实体携带 `action`（`add`/`set`/`remove`/`replace`），含判定规则与每类 action 的 few-shot 示例。
  - 输出严格 JSON schema：`{"entities":[{type,action,extraction_text,attributes}]}`，复用 `_json_call` 严格 JSON 模式与 `StructuredIntentError` 错误约定。
  - 消息构造：system=EXTRACTION_SYSTEM_PROMPT；user=参考时间行「【参考时间】YYYY-MM-DD HH:MM（星期X）」+ history 上下文段 + 用户本次输入。
- **原因**: 实体提取器只提取名词性实体，丢失"加/改/删/换"等操作语义，下游 merge 无法区分累加与覆盖、新增与删除（如"再加一吨苹果"与"我要两吨苹果"提取结果相同但动作相反）。需扩展 action 维度，让每个实体携带操作语义供 merge 依据。
- **关联**: OpenSpec change `extend-extract-with-action-semantics`
- **评测结果**:
  - `conda run -n agent python -m pytest -q` → 52 passed。
  - 新增 `tests/test_extract.py`：prompt 内容断言（action 枚举、14 类实体、归一规则、few-shot）、action 四类提取（add/set/remove/replace）、实体类型覆盖与归一（location 角色、vehicle_type 归一值、cargo 属性、time history context）、解析健壮性（非法 JSON/非法 action/缺字段/非数组/非对象 → StructuredIntentError）、输入参数注入（参考时间含星期、history 段、system/user 消息顺序）。
  - 尚未接入图执行（会话状态载体未引入），extract 作为纯函数独立测试。
  - 尚无真实 LLM 评测集；action 判定与实体归一准确率待评测集补充。
