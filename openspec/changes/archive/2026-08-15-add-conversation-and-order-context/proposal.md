## Why

当前实体提取器已经能够输出带 `action` 的订单实体，但项目没有持久化多轮对话和当前订单草稿的状态，提取结果无法跨轮累积或应用到订单字段。引入会话历史、单订单上下文和 reducer，可以为后续图接入与真实订单业务提供稳定的状态基础。

## What Changes

- 新增 `HistoryConversation`，保存当前会话的 user/assistant/system turns，并支持最近消息和 LLM 消息格式化。
- 新增单订单 `OrderContext`，覆盖 extract 当前支持的订单字段。
- 新增 `ConversationSession`，组合会话历史和 active order context。
- 新增 `OrderContextReducer`，将 Entity 的 `set`、`add`、`remove`、`replace` action 应用到订单上下文。
- 为货物列表、单值字段、备注和车型规格定义明确的 action 行为。
- 增加模型序列化、状态更新和 reducer 单元测试。
- 第一阶段不接入数据库、CLI 持久化、历史订单查询和真实订单业务执行。

## Capabilities

### New Capabilities

- `conversation-order-context`：提供多轮会话历史、当前订单草稿上下文及实体 action 合并能力。

### Modified Capabilities

无。

## Impact

- 新增 `src/inorder_llm/context/` 领域模块及测试。
- 复用 `extract.Entity` 和现有实体字段定义，不修改 LLM 提取协议。
- 后续 LangGraph 可注入或返回这些状态，但本 change 不改变现有图拓扑和 CLI 行为。
- 不新增外部依赖。
