## Context

当前意图识别子图只识别主意图（order/qa）与粗粒度子意图（create_order/modify_draft/query_history_order），不提取订单实体字段。下单流程的 extract 层缺失：用户已有现成的 langextract 实体提取 prompt（覆盖 14 类实体 + 语义归一规则），但该 prompt 只提取名词性实体，不表达"加/改/删/换"等操作语义，且尚未接入代码。

本 change 引入 extract 模块并扩展 action 维度，作为下单流程 extract 层的第一块基石。会话状态载体（history、ordercontext、reference_time 的会话级持久化）留给后续 change。

## Goals / Non-Goals

**Goals:**
- 定义带 `action` 字段的 `Entity` 模型。
- 引入并扩展 langextract prompt：保留原 14 类实体与归一规则，新增 action 判定维度。
- extract 作为纯函数，输入 `message` + `history` + `reference_time` 显式传入，可独立测试。
- 输出解析为 `Entity` 列表，复用现有 `StructuredIntentError` 错误约定。

**Non-Goals:**
- 不接入意图图/下单图执行（依赖会话状态载体未就位）。
- 不引入会话状态载体（CliSession 持有 history/ordercontext 等）。
- 不实现 merge、rewrite、ordercontext 领域模型。
- 不建立真实 LLM 评测集（用 mock LLM 单测）。

## Decisions

### 决策1：action 挂载在每个实体上，而非全局操作

每个 `Entity` 携带自己的 `action` 字段。

**理由**：动作和实体在用户原话里是耦合的（"加一吨苹果"=动作+实体一体），一起提取最自然；merge 拿到 `(action, entity)` 对即可逐个 apply，无需额外对齐"哪个动作作用哪个实体"。

**替代方案**：全局操作列表（如 `{operation: add, target: cargo}`）。否决——一条消息可能含多实体多动作（"苹果再加一吨，车型换冷链"），全局操作无法精确对应到每个实体。

### 决策2：action 枚举为 add/set/remove/replace，而非 CRUD 的 create/update/delete

- `add`：增量累加（"再加一吨苹果" → cargo.weight += 1）
- `set`：覆盖设置（"我要两吨苹果" → cargo.weight = 2；首次设置也用 set）
- `remove`：删除（"苹果不要了"）
- `replace`：替换（"车型换成冷链" → vehicle_type 替换为冷链）

**理由**：cargo 这类可累加字段，`add`（累加）与 `set`（覆盖）的区分对 merge 至关重要。CRUD 的 `update` 模糊了"累加 vs 覆盖"，会让 merge 丢失关键语义。`replace` 与 `set` 的区分在于：replace 隐含"替换掉某个已有值"（车型、地址等单值字段），set 是"设置/声明值"（含首次）。

**替代方案**：CRUD（create/update/delete）。否决——update 无法表达累加语义。

### 决策3：extract 作为纯函数，输入显式传入

`extract_entities(message, history, reference_time) -> List[Entity]`，不持有会话状态，不依赖全局可变状态。

**理由**：会话状态载体（CliSession 持有 history/ordercontext）尚未引入。纯函数可独立测试，输入由调用方提供。后续接入图时，节点从 state 取 history/reference_time 调用此函数即可。

**替代方案**：从会话单例/全局取 history。否决——耦合未引入的会话状态，无法独立测试。

### 决策4：prompt 基于现成 _PROMPT_TEMPLATE 扩展 action 维度

保留原 prompt 的 14 类实体定义与所有语义归一规则（时间归一、车型归一、地址角色、人名拆分等），新增：
- action 维度说明：要求模型对每个实体判断本轮操作（add/set/remove/replace）。
- action 判定规则：首次出现/无明确动作 → set；"加/再/多" → add；"不要了/删/取消" → remove；"换/改成" → replace。
- few-shot 示例扩展：每个 action 至少一个示例，输出含 action 字段。

**消息构造**（参考 resolver 模式）：system message = 扩展后的 prompt；user message = 参考时间行 + history 上下文 + 用户本次输入。reference_time 按"【参考时间】YYYY-MM-DD HH:MM（星期X）"格式作为 user message 第一行。history 格式化为对话上下文段注入 user message。

### 决策5：输出 JSON schema

LLM 返回严格 JSON：
```
{
  "entities": [
    {"type": "cargo", "action": "add", "extraction_text": "一吨苹果",
     "attributes": {"name": "苹果", "weight": "1吨"}},
    ...
  ]
}
```
复用 resolver 的 `_json_call` 严格 JSON 模式（仅 JSON、无多余文本）。

### 决策6：模块结构

`src/inorder_llm/extract/`：
- `models.py` — `Entity` dataclass（type/action/attributes/extraction_text）。
- `prompt.py` — `EXTRACTION_SYSTEM_PROMPT` 常量。
- `extractor.py` — `EntityExtractor` 类（持 LLM client）+ `extract_entities` 函数。
- `parser.py` — `parse_entities` 解析函数。

**理由**：与 `intent/` 模块结构对称（models/prompt/resolver 分离）。extractor 持 client（类比 LLMIntentModel），parser 纯解析可独立测试。

### 决策7：错误处理复用 StructuredIntentError

JSON 解析失败、action 非法枚举值、必要字段缺失时，抛出 `StructuredIntentError`（位于 `intent/resolver.py`，extract 导入复用）。

**理由**：与意图识别层错误处理一致，下游可统一捕获。避免新建平行错误类型。

## Risks / Trade-offs

- **[prompt 复杂度影响实体提取质量]** 原 prompt 已较满（14 类 + 归一规则），加 action 维度可能让模型注意力分散，影响实体提取准确率。→ 用 few-shot 示例覆盖四类 action，单测验证关键 case；后续建真实 LLM 评测集对比。
- **[LLM 时间归一不可靠]** 时间归一规则复杂（开闭区间、相对时间推算），LLM 算术易错。→ 单测覆盖关键归一 case；承认 LLM 算术不可靠是已知风险，归一结果可考虑后续加确定性校验层。
- **[cargo 首次输入的 add/set 模糊]** "我要两吨苹果"在无现有 cargo 时，add 与 set 等价。→ 规则：无明确动作动词时默认 set；prompt 指导。merge 层处理"无现有实体时 add 退化为 set"。
- **[history 注入格式未定]** 本 change 的 extract 接收 history 参数，但 history 注入 prompt 的具体格式（全文拼接 vs 摘要 vs 角色 message）未定。→ 设计为参数，注入格式在接入图时定；本 change 用简单拼接足以测试。
- **[action 与意图层子意图职责重叠]** 意图层 modify_draft 是粗粒度动作，extract 的 action 是细粒度动作。→ 两者层级不同：意图层判方向（create/modify/query），extract 层判字段操作（add/set/remove/replace）。文档说明边界，避免混淆。

## Open Questions

- history 注入 prompt 的具体格式（对话历史如何拼进 user message）——接入图时定，不影响本 change 的函数契约。
- cargo 多 item 场景的 add 语义（"加一吨苹果"在已有苹果时是同 item 加量还是新 item）——留给 merge 层，extract 只输出 action=add + 实体属性。
