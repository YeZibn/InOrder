## Context

当前 `CliSession` 已持有 `HistoryConversation` 和 `OrderContext`，普通消息成功后会生成最终 CLI 输出，但尚未把 assistant 结果写入 history，也没有查看 session 内容的命令。现有模型已经提供 `to_dict()`，可直接用于合法 JSON 序列化。

## Goals / Non-Goals

**Goals:**

- 在 graph 成功后生成稳定、短小的 assistant 摘要并追加到 history。
- 支持 `/context` 和 `/conversation` 只读查看当前内存 session。
- 保持命令与业务 graph 解耦，查看命令不触发推理。
- 保证 graph/reducer 异常时不写入 assistant 摘要。

**Non-Goals:**

- 不保存完整 CLI 输出、实体列表或原始 LLM content 到 history。
- 不实现 session 切换、跨进程持久化、文件或数据库存储。
- 不改变 OrderContext 字段和 reducer 规则。

## Decisions

1. **摘要从结构化结果生成，而不是截取 CLI 文本。**
   增加内部 summary builder，根据链路和结果字段拼接单行摘要。这样避免把 Entity JSON、完整上下文和调试标记带入下一轮 prompt。

2. **assistant 摘要只在处理成功后写入。**
   `handle_message` 先追加 user，执行 runner；runner 成功后生成摘要并 append assistant。异常直接向上抛出，不能追加伪成功摘要。

3. **查看命令使用模型序列化结果。**
   `/context` 返回 `json.dumps(session.order_context.to_dict(), ensure_ascii=False, indent=2)`；`/conversation` 返回 `json.dumps(session.history.to_dict(), ensure_ascii=False, indent=2)`。两者只读，不写入 history。

4. **assistant metadata 保留少量机器字段。**
   assistant turn 的 metadata 可保存 `chain`、`main_intent`、`entity_count`、`order_context_updated` 等摘要所需字段，content 保持人类可读短文本；不保存原始响应。

5. **CLI 输出与 history 摘要分离。**
   现有详细 CLI 输出继续用于当前终端查看；history 只保存 summary，避免后续 rewrite 上下文膨胀。

## Risks / Trade-offs

- [Risk] 摘要过短可能丢失业务细节 → 保留主意图、澄清原因、实体数量和上下文更新状态等最小状态集合。
- [Risk] 结果对象类型在不同链路有差异 → summary builder 对 full/order/intent 分支做显式处理并提供稳定兜底文本。
- [Risk] 当前 history 可能包含本轮 user 后才执行 graph → assistant 只在成功后追加，失败时保留用户原始输入以便诊断。

