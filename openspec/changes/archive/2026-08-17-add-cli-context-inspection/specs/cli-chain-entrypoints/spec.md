## ADDED Requirements

### Requirement: Inspect current session context

CLI SHALL 提供只读命令查看当前 session 的结构化订单上下文和会话历史，不改变任何 session 状态。

#### Scenario: Show order context

- **WHEN** 用户输入 `/context`
- **THEN** CLI 以 JSON 形式输出当前 `OrderContext` 的完整可序列化内容

#### Scenario: Show conversation history

- **WHEN** 用户输入 `/conversation`
- **THEN** CLI 以 JSON 形式输出当前 `HistoryConversation` 的有序 turns

#### Scenario: Inspection commands are side-effect free

- **WHEN** 用户执行 `/context` 或 `/conversation`
- **THEN** CLI 不调用任何 graph、不追加 history、不修改 OrderContext

#### Scenario: Empty inspection output

- **WHEN** 当前 session 没有历史或订单字段
- **THEN** CLI 仍返回合法 JSON，分别展示空 turns 和默认空上下文字段

