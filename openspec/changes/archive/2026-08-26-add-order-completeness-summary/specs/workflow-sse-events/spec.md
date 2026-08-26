## MODIFIED Requirements

### Requirement: Emit a stable SSE frame format

系统 SHALL 将每个业务事件编码为一个独立 SSE 数据帧，数据内容为 JSON 对象，且至少包含字符串字段 `type` 和对象字段 `payload`。正常完成订单工作流时，`DONE.payload.result` SHALL 包含结构化订单摘要、面向用户的自然语言回复及完整性状态，同时继续提供客户端兼容所需的结构化业务结果。

#### Scenario: Encode a workflow event

- **WHEN** 工作流发布一个阶段事件
- **THEN** 响应发送形如 `data: {"type":"<EVENT_TYPE>","payload":{...}}\n\n` 的 SSE 帧

#### Scenario: Complete an order stream with summary

- **WHEN** 订单工作流正常完成
- **THEN** 系统发送一个 `DONE` 事件，其结果包含可直接展示给用户的自然语言回复、结构化状态及缺失字段信息，并结束响应；客户端 SHALL 将自然语言回复追加到主对话框的助手消息列表，同时可更新右侧摘要面板，不直接渲染原始 JSON 或内部状态字段

#### Scenario: Show the final summary in the main conversation

- **WHEN** Web 客户端收到包含订单摘要的 `DONE` 事件
- **THEN** 客户端从 `order_result.order_summary.user_message`（兼容顶层 `order_summary.user_message`）读取文案，并在主对话框追加一条助手消息；同一 `DONE` 事件不得重复追加消息

#### Scenario: Preserve compatibility for responses without an order summary

- **WHEN** Web 客户端收到非订单结果或不包含 `order_summary.user_message` 的兼容 `DONE` 事件
- **THEN** 客户端不追加订单摘要助手消息，继续按既有方式展示普通完成状态和结构化结果

#### Scenario: Complete a non-order stream

- **WHEN** 非订单工作流正常完成
- **THEN** 系统继续发送兼容的 `DONE` 事件，不要求生成订单完整性摘要
