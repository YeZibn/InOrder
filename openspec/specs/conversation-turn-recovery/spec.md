# conversation-turn-recovery Specification

## Purpose

在网络中断或客户端异常后识别未完成的会话回合，将悬空用户消息与下一次输入安全合并并恢复为可持久化的完整会话状态。

## Requirements

### Requirement: Detect pending conversation turns

系统 SHALL 在工作流入口检查传入的 `HistoryConversation`，将最后一条消息为 `user` 且其后没有 `assistant` 回复的消息判定为未完成回合；不得将 `system` 消息视为 assistant 回复。

#### Scenario: Complete history
- **WHEN** history 最后一条消息为 assistant
- **THEN** 系统判定不存在未完成回合并仅处理本次 message

#### Scenario: Pending user turn
- **WHEN** history 最后一条消息为 user 且没有后续 assistant
- **THEN** 系统识别该 user 消息为 pending turn

#### Scenario: Consecutive pending users
- **WHEN** assistant 回复之后存在连续多条 user 消息
- **THEN** 系统将这些消息按顺序合并为一个待恢复消息块，不重复处理同一条消息

### Requirement: Merge and replay pending input

系统 SHALL 在存在 pending turn 时，将 pending 消息与本次新 message 合并后执行一次工作流；合并文本必须保留原始消息顺序。对于“重试”“继续”“再试一次”等控制输入，系统 SHALL 只重放 pending 消息，不把控制词作为订单语义。

#### Scenario: Merge new business message
- **WHEN** pending 消息为“我要运一吨苹果”且本次输入为“从温州到上海”
- **THEN** 工作流收到包含两部分且顺序正确的合并输入，并只执行一次

#### Scenario: Retry control message
- **WHEN** 存在 pending 消息且本次输入为“重试”
- **THEN** 系统只重放 pending 消息，工作流输入不包含“重试”订单内容

#### Scenario: Avoid duplicate merge
- **WHEN** 本次输入与 pending 消息完全相同
- **THEN** 系统只处理一份消息，不重复拼接

### Requirement: Persist recovered history

成功完成恢复后，系统 SHALL 返回规范化的 history 或等价 `history_patch`，其中 pending user 消息与本次输入形成单个 user 回合，并包含本次 assistant 摘要；调用方可直接使用该结果替换本地历史。

#### Scenario: Successful recovery returns history
- **WHEN** pending 消息与本次输入处理成功并生成 assistant 内容
- **THEN** DONE 结果包含恢复后的 history 或 `history_patch`，且最后一个回合完整

#### Scenario: Failed recovery keeps pending state
- **WHEN** 工作流处理失败或连接在 DONE 前中断
- **THEN** 系统不得伪造 assistant 回复，调用方仍可保留 pending user 回合以便后续重试
