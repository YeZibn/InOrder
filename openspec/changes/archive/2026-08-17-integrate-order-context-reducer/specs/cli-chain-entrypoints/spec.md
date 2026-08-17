## MODIFIED Requirements

### Requirement: Preserve order parsing context

CLI SHALL 为 `order` 和 `full` 链路提供当前消息、`HistoryConversation`、`OrderContext` 和参考时间，并在订单处理子图返回新上下文时保存到当前内存 session。

#### Scenario: Order chain passes context

- **WHEN** 用户在 `order` 链路输入消息
- **THEN** 订单处理子图收到当前历史、订单上下文和参考时间

#### Scenario: Order chain persists updated context

- **WHEN** `order` 链路返回更新后的订单上下文
- **THEN** CLI 将该上下文保存为当前 session 的 `OrderContext`，供下一轮输入使用

#### Scenario: Full chain persists updated context

- **WHEN** `full` 链路识别主意图为 `order` 且订单处理子图返回更新后的订单上下文
- **THEN** CLI 将该上下文保存为当前 session 的 `OrderContext`

#### Scenario: Clear resets conversation state

- **WHEN** 用户输入 `/clear`
- **THEN** CLI 清空消息、历史对话和订单上下文，同时保留当前链路和 CLI 运行状态

### Requirement: Expose order processing stage status

full 和 order 链路 SHALL 暴露订单处理阶段状态，至少区分是否进入订单处理子图、rewrite 是否完成、extract 是否执行或跳过、最终实体数量，以及订单上下文是否更新。

#### Scenario: Extraction status is observable

- **WHEN** extract 成功返回实体列表
- **THEN** CLI 显示 `extract` 已执行和实体数量

#### Scenario: Skipped extraction status is observable

- **WHEN** rewrite 触发澄清并跳过 extract
- **THEN** CLI 显示 `extract` 已跳过及跳过原因

#### Scenario: Context update status is observable

- **WHEN** 订单处理子图返回更新后的订单上下文
- **THEN** CLI 输出订单上下文已更新的状态

