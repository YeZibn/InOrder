## MODIFIED Requirements

### Requirement: Preserve order parsing context

CLI SHALL 为 `order` 和 `full` 链路提供当前消息、`HistoryConversation`、`OrderContext` 和参考时间，并在订单处理子图返回新上下文时保存到当前内存 session。参考时间 SHALL 在每条用户消息进入处理时确定一次；调用方提供的有效参考时间优先使用，未提供时使用当前 `Asia/Shanghai` 时间。Rewrite、Extract 及本轮重试 SHALL 复用该值。

#### Scenario: Order chain passes context
- **WHEN** 用户在 `order` 链路输入消息
- **THEN** 订单处理子图收到当前历史、订单上下文和本轮确定的参考时间

#### Scenario: Order chain persists updated context
- **WHEN** `order` 链路返回更新后的订单上下文
- **THEN** CLI 将该上下文保存为当前 session 的 `OrderContext`，供下一轮输入使用

#### Scenario: Full chain persists updated context
- **WHEN** `full` 链路识别主意图为 `order` 且订单处理子图返回更新后的订单上下文
- **THEN** CLI 将该上下文保存为当前 session 的 `OrderContext`

#### Scenario: Generate reference time per message
- **WHEN** CLI 处理一条新的用户消息且没有外部 reference_time
- **THEN** CLI 在消息处理开始时生成一次 Asia/Shanghai 参考时间，并将其传递给本轮工作流，不复用 session 初始化时的旧时间

#### Scenario: Keep reference time stable across nodes
- **WHEN** 一条用户消息依次经过 Rewrite、Extract、货物画像或车型节点
- **THEN** 各节点使用同一个 reference_time，节点重试不得重新取当前时间

#### Scenario: Clear resets conversation state
- **WHEN** 用户输入 `/clear`
- **THEN** CLI 清空消息、历史对话和订单上下文，同时保留当前链路和 CLI 运行状态
