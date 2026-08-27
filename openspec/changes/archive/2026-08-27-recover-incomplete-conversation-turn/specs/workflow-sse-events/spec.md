## MODIFIED Requirements

### Requirement: Done event carries recovery state

SSE 工作流在成功结束时 SHALL 通过 `DONE` 事件返回恢复后的会话 history 或 `history_patch`；`ERROR` 事件不得伪造 assistant 内容，客户端可依据该状态决定保留 pending user 回合并重试。

#### Scenario: DONE includes recovered history
- **WHEN** 工作流成功完成一次包含 pending turn 的恢复请求
- **THEN** DONE payload 包含可持久化的 history 或 history_patch，且不含重复 user 消息

#### Scenario: ERROR preserves retryability
- **WHEN** 工作流在 DONE 前发生网络或服务错误
- **THEN** ERROR payload 不包含 assistant 摘要，并保留可重试标识或既有 pending history
