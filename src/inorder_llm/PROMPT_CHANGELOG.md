# Prompt 变更记录

本文件记录 `inorder_llm` 中所有 LLM prompt 的变更、原因与评测结果。按 **prompt 常量** 分层组织，每个 prompt 下按日期倒序排列变更（最新记录在前，最早记录在后），以便优先查看当前规则。当前覆盖 `intent/resolver.py`（`MAIN_INTENT_SYSTEM_PROMPT` / `SUB_INTENT_SYSTEM_PROMPT`）与 `extract/resolver.py`（`EXTRACTION_SYSTEM_PROMPT`）；后续新增的 prompt 常量同样在此记录。

## 记录格式

每个 prompt 常量为一个 `###` 标题（标注所在文件），其下按日期（`####`）倒序排列变更记录。每条记录包含以下字段：

| 字段 | 说明 |
| --- | --- |
| 日期 | 变更日期 (YYYY-MM-DD)，以系统真实日期为准（运行 `date "+%Y-%m-%d %A"` 确认） |
| 变更摘要 | 改了什么（新旧差异要点），聚焦本 prompt 的具体变化 |
| 原因 | 为什么改（动机 / 触发场景） |
| 关联 | OpenSpec change / commit / PR |
| 评测结果 | 变更后的验证情况：单测通过情况、prompt 内容 / 消息角色断言、典型 case 表现、（如有）真实 LLM 评测集得分、回归情况 |

> 评测结果应尽量给出可复现的依据（命令、用例、得分），而不只是「通过」。

> **时间顺序约定**：同一 prompt 下日期必须严格按倒序排列，最新日期放在最前面；新增记录必须插入到该 prompt 标题后的第一条记录，不得直接追加到历史记录末尾。不同 prompt 之间仍按代码模块的既有分组顺序排列。

## 记录

### `MAIN_INTENT_SYSTEM_PROMPT`（`intent/resolver.py`）

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

---

### `SUB_INTENT_SYSTEM_PROMPT`（`intent/resolver.py`）

#### 2026-08-15

- **变更摘要**:
  - `create_order` 加入「运货/发货/配送/托运等运输需求均映射为此子意图」领域映射。
- **原因**: 主意图已将业务目标词（运货/发货等）纳入 `order`，子意图层需同步覆盖，避免主意图判 `order` 但子意图无法匹配 `create_order`。
- **关联**: OpenSpec change `broaden-order-intent-to-business-goals`（已归档）
- **评测结果**:
  - `conda run -n agent python -m pytest -q` → 29 passed。
  - 无新增 SUB 专属断言（本次改动为单行领域映射补充，回归通过即可）。
  - 尚无真实 LLM 评测集。

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

---

### `EXTRACTION_SYSTEM_PROMPT`（`extract/resolver.py`）

#### 2026-08-19T16:25:21+0800

- **变更摘要**:
  - location 从仅提取 `city` 扩展为支持 `city` 与用户原文中的连续 `full_address`。
  - 增加城市级、详细仓库/园区地址和缺少城市时保留完整地址的规则与示例。
  - 明确不得从上下文补全、拆分、标准化或改写地址。
- **原因**: 物流装卸地址不能只停留在城市级，需要保留园区、仓库和市场等具体地址，同时保持 grounded extraction 的原文边界。
- **关联**: OpenSpec change `extend-location-address`。
- **评测结果**:
  - `conda run -n agent python -m pytest -q tests/test_extract.py tests/test_langextract_adapter.py tests/test_context.py tests/test_order_processing_graph.py` → 69 passed, 1 skipped。
  - `tests/test_extract.py` 覆盖详细地址、城市缺失、来源边界；`tests/test_context.py` 覆盖 pickup/dropoff 映射保留。
  - 尚无真实 LLM 评测集，待补充。

#### 2026-08-17

- **变更摘要**:
  - 将 `vehicle_type` 收敛为基础车型和标准车长，并在 `attributes.value` 中使用车型目录 code。
  - 将冷链、厢式、高栏、平板、危险品、高顶和尾板明确归入 `vehicle_specs`，每个规格独立输出。
  - 增加冷链单规格、车长+冷链+厢式组合和车长+多规格 few-shot；保留 `extraction_text` 的用户原文。
- **原因**: 原 prompt 将冷链车错误归为 `vehicle_type`，且车型与规格边界不清，无法为后续车型归一化提供稳定词汇契约。
- **关联**: OpenSpec change `add-vehicle-catalog-and-spec-prompt`
- **评测结果**:
  - `conda run -n agent python -m pytest -q` → 111 passed；`tests/test_extract.py` 已覆盖车型/规格边界、目录 code 和原文保留断言。
  - 尚无真实 LLM 评测集，待补充。

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

---

### `LANGEXTRACT_ORDER_PROMPT_DESCRIPTION`（`extract/resolver.py`）

#### 2026-08-19T16:25:21+0800

- **变更摘要**:
  - LangExtract location attributes 增加 `full_address`，并补充城市级与详细地址 few-shot。
  - 适配层校验 `full_address` 必须来自当前 extraction source，不进行本地地址推断。
- **原因**: 让 LangExtract backend 与 JSON backend 使用一致的 city/full_address 地址契约，并支持具体装卸点。
- **关联**: OpenSpec change `extend-location-address`。
- **评测结果**:
  - `conda run -n agent python -m pytest -q tests/test_extract.py tests/test_langextract_adapter.py tests/test_context.py tests/test_order_processing_graph.py` → 69 passed, 1 skipped。
  - `tests/test_langextract_adapter.py` 覆盖 prompt alignment、详细地址保留和来源边界。
  - 尚无真实 LLM 评测集，待补充。

#### 2026-08-17T23:17:05+0800

- **变更摘要**:
  - prompt 与 schema-covering examples 移至 `extract/resolver.py`，覆盖 14 类订单实体；extract 仅消费 rewrite 文本和参考时间。
  - 强制 examples 覆盖完整实体类型与 attributes，使 LangExtract strict schema 不再仅允许 cargo/location。
  - 明确 LLM 是 action、地址 role 与业务字段的唯一决策方；原文 remark 与摘要 value 分离。
- **原因**: 初始 prompt 的 examples 只能生成 cargo/location schema，且 extract 读取 history 可能重新提取旧订单实体。
- **关联**: OpenSpec change `strengthen-langextract-prompt-contract`（已归档）。
- **评测结果**:
  - `conda run -n agent python -m pytest -q` → 147 passed, 2 skipped。
  - `INORDER_LLM_LIVE_TESTS=1 conda run -n agent python -m pytest -q tests/test_langextract_adapter.py` → 15 passed，覆盖基础订单、车型规格与 remark。
  - 断言位于 `tests/test_langextract_adapter.py`；尚无系统化真实 LLM 评测集，待补充。

#### 2026-08-17（历史记录，精确时间未保存）

- **变更摘要**:
  - 初始引入 LangExtract grounded extraction description 与 cargo/location few-shot。
  - 将 action 放入 attributes，并保留原文片段与对齐元数据。
- **原因**: 替代旧 JSON 提取器，减少合法 JSON 但语义为空的提取结果。
- **关联**: OpenSpec change `rebuild-extract-with-langextract`（已归档）。
- **评测结果**:
  - 初始 adapter 聚焦测试与真实基础订单探针通过；精确命令统计已由后续完整契约记录取代。

---

### `REWRITE_SYSTEM_PROMPT`（`rewrite/resolver.py`）

#### 2026-08-20T14:55:09+0800

- **变更摘要**:
  - 移除 rewrite 输出中的 `needs_clarification` 和 `clarification_reason`。
  - 要求存在歧义时根据当前订单上下文和最近对话选择最合理解释，继续生成可执行的 `extraction_text`。
- **原因**: rewrite 澄清会直接跳过 extract，阻断订单语义链路；当前阶段改为最佳努力解析。
- **关联**: OpenSpec change `remove-rewrite-clarification`
- **评测结果**:
  - `conda run -n agent python -m pytest -q` → 172 passed, 2 skipped。
  - `tests/test_rewrite.py` 和 `tests/test_order_processing_graph.py` 覆盖无澄清字段、歧义仍进入 extract 及非法 JSON 校验。
  - 尚无真实 LLM 评测集，待补充。

---

#### 2026-08-15

- **变更摘要**:
  - 新增订单语义重写 prompt，输入分为当前订单上下文、最近对话历史和用户本轮输入。
  - 明确用户本轮输入、OrderContext、HistoryConversation 的优先级和保守指代消解规则。
  - 增加 `rewritten_text` 与 `extraction_text` 双文本输出，后者只描述本轮增量语义。
  - 明确 add/set/remove/replace 与中文动作表达的映射，并规定无法唯一消歧时返回澄清状态。
- **原因**: 订单 extract 需要保留多轮输入中的增量动作，避免把已有 OrderContext 重复提取为 set，从而破坏 add/remove/replace 语义。
- **关联**: OpenSpec change `add-order-rewrite-node`
- **评测结果**:
  - `conda run -n agent python -m pytest -q` → 65 passed。
  - `tests/test_rewrite.py`：覆盖 RewriteResult 序列化、增量货物、上下文分区、消息角色、prompt 动作规则、非法 JSON/字段和澄清结果。
  - 当前尚无真实 LLM 评测集；rewrite 与实体提取联调待后续接入订单子图后补充。

---

### `CARGO_PROFILE_SYSTEM_PROMPT`（`cargo_profile/resolver.py`）

#### 2026-08-20T14:07:42+0800

- **变更摘要**:
  - 强化“货物类型 + 运输规模信息”时的强制估算规则，加入从单件参数、包装、堆积密度到装车占用空间的推理链。
  - 增加“一吨苹果”和“100箱苹果”典型场景约束，禁止在可推理时返回总体积或尺寸 `null`。
  - 明确 `dimensions_cm` 表示整体装车占用尺寸，并保留仅有货物名称时允许 `null` 的边界。
- **原因**: 实际输出中“一吨苹果”被错误判定为无法估算总体积，导致后续车型空间校验缺少输入。
- **关联**: OpenSpec change `force-cargo-profile-estimation`
- **评测结果**:
  - `conda run -n agent python -m pytest tests/test_cargo_profile.py -q` → 9 passed。
  - `conda run -n agent python -m pytest -q` → 172 passed, 2 skipped。
  - `tests/test_cargo_profile.py` 新增一吨苹果、100箱苹果及仅货物名称边界场景。
  - 尚无真实 LLM 评测集，待补充。

---

#### 2026-08-20T10:45:11+0800

- **变更摘要**:
  - 将画像输出简化为 `weight_kg`、`volume_m3`、`dimensions_cm`、运输属性和 `reason`。
  - 删除 `raw`、`unit`、`basis`、`confidence`、`assumptions`、`warnings` 等字段要求。
  - 规定有可用信息时必须尽力估算核心数值，只有完全无法估算时才允许 `null`。
- **原因**: 为后续车型载重和货厢尺寸校验提供直接输入，避免字段过度复杂或在可估算时无理由返回空值。
- **关联**: OpenSpec change `simplify-cargo-profile-estimation`
- **评测结果**:
  - `conda run -n agent python -m pytest -q` → 170 passed, 2 skipped。
  - `tests/test_cargo_profile.py` 覆盖简化 schema、非空 reason、可估算与完全无法估算场景。
  - 尚无真实 LLM 评测集，待补充。

---

#### 2026-08-19T15:36:52+0800

- **变更摘要**:
  - 新增完整货物快照的约束画像 prompt，输出数量、重量、尺寸、装车占用体积、可堆叠性、易碎性、温度要求及汇总。
  - 强制每个字段标注 `basis`、`confidence`，并要求记录估算假设与不确定性警告。
  - 明确画像不得选择车型、输出车辆 code 或装箱坐标；原始 cargo 表达必须通过 `raw` 字段保留。
- **原因**: 为后续车辆边界校验提供可解释的派生货物约束，同时保持原始货物事实不被覆盖。
- **关联**: OpenSpec change `add-cargo-profile`。
- **评测结果**:
  - `conda run -n agent python -m pytest -q tests/test_cargo_profile.py tests/test_context.py tests/test_order_processing_graph.py tests/test_intent_cli.py` → 49 passed。
  - 断言位于 `tests/test_cargo_profile.py`，覆盖 prompt 规则、严格 JSON、原始表达保留、未知/partial 汇总、枚举及禁止车辆字段。
  - 尚无真实 LLM 评测集，待补充。
