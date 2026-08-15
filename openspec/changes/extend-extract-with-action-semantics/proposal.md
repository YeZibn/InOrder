## Why

当前实体提取器（langextract）只提取名词性实体（货物、地点、车型、时间等），无法表达"加/改/删/换"等操作语义。在增量/修改场景下（如"再加一吨苹果""苹果不要了"），提取结果丢失动作，下游 merge 无法区分累加与覆盖、新增与删除。需要扩展 extract 层，让每个实体携带 `action`，为后续 merge 提供可依据的操作语义。

## What Changes

- 新增 `Entity` 模型，每个提取出的实体携带 `action` 字段（`add` / `set` / `remove` / `replace`）。
- 引入 langextract 实体提取 prompt（含现有 14 类实体类型与语义归一规则），并扩展 action 维度：要求模型对每个实体判断本轮对其应用的操作。
- 新增 extract 函数：输入 `message` + `history` + `reference_time`，输出带 `action` 的实体列表。输入以显式参数传入，不耦合会话状态载体。
- 新增输出解析，将 LLM 返回的结构化结果解析为 `Entity` 列表，复用现有 `StructuredIntentError` 错误处理约定。
- 新增单元测试，覆盖 action 提取（add/set/remove/replace 四类）、归一实体与解析健壮性。

## Capabilities

### New Capabilities
- `order-entity-extraction`: 从用户自然语言输入中提取带操作语义（action）的订单实体，作为下单流程 extract 层的基础。覆盖实体类型、语义归一规则与 action 判定，输出可供 merge 消费的结构化实体列表。

### Modified Capabilities
<!-- 无。本 change 不改动现有意图识别子图（intent-planning / langgraph-intent-graph）的 spec 行为。extract 作为独立能力，暂不接入图执行。 -->

## Impact

- 新增代码：`src/inorder_llm/extract/`（models / prompt / extractor / parser）。
- 新增测试：`tests/test_extract.py`。
- 不改动现有意图识别子图、CLI 与 resolver。
- 不引入会话状态载体（history、reference_time 作为 extract 函数的显式输入参数，由调用方提供；会话级伴随状态留给后续 change）。
- 不实现 merge、rewrite、ordercontext 模型（留给后续 change）。
