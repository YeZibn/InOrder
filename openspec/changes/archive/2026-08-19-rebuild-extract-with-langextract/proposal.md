## Why

当前 extract 需要从严格 JSON 提取迁移到 LangExtract grounded extraction，同时必须避免 adapter 以关键词、实体顺序或默认值二次推断订单语义。用户要求以 LLM 的 grounded 输出作为唯一语义决策源，提升语义边界的一致性和调试可解释性。

## What Changes

- 引入 `langextract` 作为 grounded extraction 后端。
- 将提取结果重构为“类别 + 原文片段 + attributes + 提取元数据”的模型。
- 将 `action` 放入实体 attributes，由 LLM 输出；兼容层只原样复制该值到旧 `Entity.action`。
- 新增 LangExtract 到现有业务实体的无语义映射层，保留 LLM 输出的地址角色、货物字段、车型/规格 code 和原文定位元数据。
- 空提取是 LLM 的有效输出，系统原样返回空列表；不通过关键词规则将其改判为失败或澄清。
- 保持 `EntityExtractorModel`、LangGraph `ExtractNode` 和 `OrderContextReducer` 的调用边界稳定，逐步替换内部实现。
- 更新测试、依赖和 extract 文档；不改变订单上下文 reducer 的职责。

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `order-entity-extraction`: 使用 grounded extraction 结果生成带 attributes/action 的实体，且 adapter 不补全、不改写或重新判断实体语义。
- `order-processing-subgraph`: 订单子图继续消费统一提取接口，但接入新的 LangExtract 实现和失败边界。

## Impact

- Affected code:
  - `src/inorder_llm/extract/`
  - `src/inorder_llm/graph/order/`
  - `pyproject.toml`
  - tests and README
- New dependency: `langextract` and its supported model-provider configuration.
- Existing `Entity` consumers and reducer require a compatibility mapping that copies, rather than derives, semantic fields.
- No database, order API, or external business side effects.
