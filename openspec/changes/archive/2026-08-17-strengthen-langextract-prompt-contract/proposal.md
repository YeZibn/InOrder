## Why

现有 LangExtract description 只有少量规则，且 few-shot 仅覆盖 cargo 与 location。由于 OpenAI strict schema 由 LangExtract examples 推导，其他订单实体即使写在 description 中也无法稳定输出；同时 extract 直接读取历史上下文，可能把旧订单字段重新写入本轮草稿。

## What Changes

- 在 `src/inorder_llm/extract/resolver.py` 定义完整的 LangExtract prompt description、实体契约和 schema-covering few-shot examples。
- 覆盖 14 类订单实体及其 action、role、时间、备注和车型/规格 attributes 契约。
- 将 rewrite 设为 history 与 OrderContext 的唯一消费者；extract 仅基于 rewrite 的 extraction text 与 reference time 做 grounded extraction。
- 保持 LLM 为业务语义唯一决策方；adapter 只做 grounded 输出的契约校验和兼容转换。
- 增加 prompt/schema、子图输入边界与真实 LangExtract 回归测试，并记录 prompt 变更。

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `order-entity-extraction`: 完整定义 LangExtract 的 grounded prompt、examples/schema 覆盖与 LLM 语义输出契约。
- `order-processing-subgraph`: 收紧 rewrite 与 extract 的上下文边界，避免 extract 从历史或订单上下文重提取实体。

## Impact

- Affected code: `src/inorder_llm/extract/resolver.py`, `src/inorder_llm/extract/langextract_adapter.py`, `src/inorder_llm/graph/order/`, tests, prompt changelog, and README.
- LangExtract OpenAI schema 将由覆盖完整实体类别与 attributes 的 few-shot examples 生成。
- Extractor protocol 和测试替身将不再把 history 作为提取阶段的语义输入；历史解析仍由 rewrite 负责。
- 不新增外部服务、数据库或真实下单副作用。
