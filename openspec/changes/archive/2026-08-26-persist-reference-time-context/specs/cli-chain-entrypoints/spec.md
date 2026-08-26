## MODIFIED Requirements

### Requirement: Preserve order parsing context

CLI SHALL 为 `order` 和 `full` 链路提供当前消息、`HistoryConversation`、`OrderContext` 和会话级参考时间，并在订单处理子图返回新上下文时保存到当前内存 session。时间锚点 SHALL 按“上下文已有值、调用方提供的有效值、当前 `Asia/Shanghai` 时间”的顺序确定；一旦确定，后续轮次 SHALL 复用该值。Rewrite、Extract 及本轮重试 SHALL 复用同一值。

#### Scenario: First message creates reference time

- **WHEN** CLI 处理首条消息且当前 `OrderContext.reference_time` 为空
- **THEN** CLI 使用调用方提供的有效时间或当前 Asia/Shanghai 时间生成锚点，并将其写入本轮返回的 `OrderContext`

#### Scenario: Later message reuses context time

- **WHEN** CLI 处理后续消息且当前 `OrderContext.reference_time` 有值
- **THEN** CLI 将该值传入工作流，不重新查询当前时间，也不被后续请求级时间覆盖

#### Scenario: Keep reference time stable across nodes

- **WHEN** 一条用户消息依次经过 Rewrite、Extract、货物画像或车型节点
- **THEN** 各节点及节点重试使用同一个 `reference_time`

#### Scenario: Clear resets reference time

- **WHEN** 用户输入 `/clear`
- **THEN** CLI 清空消息、历史对话、订单上下文及其 `reference_time`，同时保留当前链路和 CLI 运行状态
