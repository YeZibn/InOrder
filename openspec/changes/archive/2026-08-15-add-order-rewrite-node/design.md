## Context

项目已有 `HistoryConversation`、`OrderContext`、`EntityExtractor` 和 `OrderContextReducer`。extract 已定义实体 action 语义，因此 rewrite 必须输出本轮增量文本，避免重复提取当前上下文导致 action 被误判为 set。

## Goals / Non-Goals

**Goals:**

- 提供独立、可测试的 rewrite resolver 和结果模型。
- 将当前上下文与历史转换为清晰的 prompt 分区。
- 保留 action 语义，并为后续 extract 提供 extraction_text。
- 在无法消歧时安全返回澄清状态。

**Non-Goals:**

- 不接入 LangGraph、extract 或 reducer。
- 不查询历史订单，不修改 context，不执行订单业务。
- 不让 rewrite 产生实体 action 字段；action 仍由 extract 负责最终识别。

## Decisions

### 双文本结果

`rewritten_text` 用于日志、调试和展示完整语义；`extraction_text` 只描述本轮增量请求，作为后续 EntityExtractor 的输入。相比只输出完整文本，这能保护 `Entity.action` 的 add/remove/replace 语义。

### 上下文优先级

用户本轮明确表达优先于当前 OrderContext，OrderContext 优先于历史对话；历史只用于指代、省略和明确的历史引用，不自动把旧订单写入当前订单。

### 结构化 JSON 与独立 user 消息

system 消息承载规则和 schema，user 消息承载结构化上下文与本轮输入。LLM 输出必须是 JSON，使用现有结构化错误类型处理非法输出。

### 纯函数边界

resolver 只读取 context，不能通过引用修改对象；调用方稍后将 rewrite 结果交给 extract 和 reducer。

## Risks / Trade-offs

- [rewrite 与 extract 规则可能重复] → rewrite 只保留语义动作，不输出实体 schema 或最终 action 字段。
- [历史上下文过长] → 第一版支持调用方限制最近 turns，后续再增加摘要策略。
- [歧义影响流程] → 返回明确澄清状态，不静默猜测。

## Migration Plan

1. 新增 rewrite 模型、resolver 和 prompt。
2. 增加 JSON 解析、上下文格式化和无副作用测试。
3. 运行全量测试并记录 prompt changelog。
4. 后续单独 change 将 rewrite 接入订单子图和 extract。
