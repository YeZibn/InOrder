## Why

CLI 当前虽然在内存中维护 history 和 OrderContext，但用户无法查看它们；同时 history 只保存用户输入，下一轮 rewrite 看不到上一轮处理结果。需要增加精简的 assistant 摘要和只读查看命令，形成可观察的多轮对话闭环。

## What Changes

- 每次普通消息成功处理后，将一条精简 assistant 摘要写入当前 session 的 history。
- 摘要只保留主意图、订单处理阶段、澄清状态、实体数量和上下文更新状态等最终信息，不保存完整 JSON、LLM 原始 content 或调试日志。
- 增加 `/context` 命令，以 JSON 形式输出当前 `OrderContext`。
- 增加 `/conversation` 命令，以 JSON 形式输出当前 `HistoryConversation`。
- CLI 命令本身不写入 history；处理异常时不追加 assistant 摘要。
- 暂不实现 session 切换、文件/数据库持久化或跨进程恢复。

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `conversation-order-context`: 扩展会话历史，允许记录精简 assistant 处理摘要，并提供可序列化的查看数据。
- `cli-chain-entrypoints`: 增加 `/context`、`/conversation` 只读命令及摘要写入行为。

## Impact

- Affected code:
  - `src/inorder_llm/cli/app.py`
  - `src/inorder_llm/context/models.py`（如需辅助序列化）
  - tests and README CLI documentation
- No new dependencies.
- No external side effects; all data remains in the current in-memory session.

