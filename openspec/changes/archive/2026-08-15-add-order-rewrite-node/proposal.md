## Why

当前订单实体提取器依赖单轮、明确的输入，而用户在多轮下单中经常使用省略、指代和增量表达，例如“再加一吨苹果”或“改到杭州”。需要在 extract 之前增加一个独立 rewrite 阶段，将本轮输入结合会话历史和当前订单上下文改写为可提取的增量语义，同时保留 add/set/remove/replace 动作含义。

## What Changes

- 新增 `RewriteResult`，包含完整语义 `rewritten_text`、供 extract 使用的 `extraction_text` 和澄清状态。
- 新增订单 rewrite resolver 和结构化 JSON 解析。
- 新增 rewrite system prompt，明确上下文优先级、动作保留、保守补全和歧义处理规则。
- 支持将 `HistoryConversation` 与 `OrderContext` 序列化为 rewrite 输入上下文。
- rewrite 只负责重写，不修改订单上下文、不提取实体、不查询历史订单。
- 第一阶段不接入 LangGraph、EntityExtractor 或 OrderContextReducer。

## Capabilities

### New Capabilities

- `order-rewrite`：将本轮订单输入结合会话历史和当前订单上下文重写为可提取的增量语义。

### Modified Capabilities

无。

## Impact

- 新增 `src/inorder_llm/rewrite/` 模块和对应测试。
- 复用现有 `HistoryConversation`、`OrderContext` 和 LLM client。
- 新增 prompt 常量及 `PROMPT_CHANGELOG.md` 记录。
- 不改变现有 intent graph、extract API、reducer 和 CLI 行为。
