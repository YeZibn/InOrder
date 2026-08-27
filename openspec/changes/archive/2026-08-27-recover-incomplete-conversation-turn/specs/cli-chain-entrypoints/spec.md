## MODIFIED Requirements

### Requirement: CLI recovers incomplete turns

CLI 在执行新消息前 SHALL 检查当前 `HistoryConversation` 的最后一个回合；发现 pending user 消息时，按恢复规则合并或重放，并在成功后更新本地 history，失败时保留 pending 状态。

#### Scenario: CLI retries failed turn
- **WHEN** 上一轮 CLI 处理失败且 history 末尾只有 user 消息
- **THEN** 下一次输入“重试”只重新执行该 user 消息，并在成功后追加 assistant 摘要

#### Scenario: CLI continues pending turn
- **WHEN** 上一轮 CLI 处理失败且用户输入补充信息
- **THEN** CLI 将未完成消息与补充信息合并执行一次，避免形成连续未配对 user 回合
