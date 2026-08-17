## Why

当前 rewrite 和 extract 已经分别具备可调用能力，但仍未由 LangGraph 编排，无法形成可测试的订单语义解析链路。现在先建立独立订单处理子图，可以验证上下文重写、澄清分流和实体提取的边界，同时避免过早引入归一化、订单草稿写入和业务工具。

## What Changes

- 新增独立的订单处理子图入口和 `OrderGraphState`。
- 增加 rewrite 节点，读取本轮消息、历史对话和当前 `OrderContext`。
- 增加澄清条件路由：rewrite 需要澄清时直接结束，不调用 extract。
- 增加 extract 节点，仅提取 rewrite 产生的 `extraction_text`。
- 增加统一 finalize 输出，返回 rewrite 结果、实体列表和澄清状态。
- 保持子图纯解析边界：本次不修改 `OrderContext`，不接入归一化、历史订单查询或订单业务工具。

## Capabilities

### New Capabilities

- `order-processing-subgraph`: 提供基于 LangGraph 的 rewrite → clarification → extract 订单语义解析子图。

### Modified Capabilities

无。本次先提供独立子图，不改变现有主意图图的外部契约。

## Impact

影响 `src/inorder_llm/graph/` 下新增订单子图模块、订单处理状态模型及其测试；复用现有 rewrite、extract、`HistoryConversation`、`OrderContext` 和 LLM client，不新增外部依赖，不修改 reducer、normalization 或现有主意图图。
