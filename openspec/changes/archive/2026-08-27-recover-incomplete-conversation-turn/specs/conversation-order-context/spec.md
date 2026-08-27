## MODIFIED Requirements

### Requirement: Conversation history

系统 SHALL 维护当前会话的 `HistoryConversation`，并支持识别未完成 user 回合；会话历史只表示当前会话消息，不代表历史订单数据。成功恢复后，系统 SHALL 提供可持久化的完整 user/assistant 回合快照或补丁。

#### Scenario: Session history stores concise assistant summary
- **WHEN** 一轮请求成功完成
- **THEN** history 追加当前 user 消息和精简 assistant 摘要，不写入完整内部工作流 JSON

#### Scenario: Failed request leaves pending user turn
- **WHEN** 请求在生成 assistant 摘要前失败
- **THEN** history 可保留最后一条 user 消息且不追加伪造 assistant

#### Scenario: Recovered session returns complete turn
- **WHEN** 下一轮请求成功恢复上一条 pending user 消息
- **THEN** 返回的 history 快照包含合并后的 user 内容和 assistant 摘要
