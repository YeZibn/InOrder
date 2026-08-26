## MODIFIED Requirements

### Requirement: Provide an SSE chat endpoint

系统 SHALL 提供 `POST /api/v2/chat` 接口，并在请求协商 `Accept: text/event-stream` 时以 `text/event-stream` 返回工作流事件。Python SHALL 从请求中的 `order_context.reference_time`、请求级 `reference_time` 或当前 `Asia/Shanghai` 时间按优先级确定一个会话时间锚点，将其写入工作流 state，并在更新后的 `OrderContext` 快照中返回。

#### Scenario: Accept a chat request

- **WHEN** 客户端提交包含 `session_id`、`message`、可选 `history`、可选 `order_context` 和可选 `reference_time` 的 JSON 请求
- **THEN** 系统使用这些字段执行一次 full 工作流，并确定或复用一个有效的会话 `reference_time`

#### Scenario: Reuse context reference time

- **WHEN** `order_context.reference_time` 存在且格式有效
- **THEN** 系统使用该值作为本次工作流时间锚点，即使请求级 `reference_time` 缺失或不同

#### Scenario: Generate and persist first reference time

- **WHEN** 上下文没有 `reference_time` 且请求级 `reference_time` 为空
- **THEN** Python 在启动工作流前生成当前 Asia/Shanghai 时间，格式为 `YYYY-MM-DD HH:MM`，并将该值写入返回的 `OrderContext`

#### Scenario: Preserve caller-provided reference time

- **WHEN** 上下文没有时间且客户端提供格式有效的 `reference_time`
- **THEN** 系统使用调用方提供的值，不以本机当前时间覆盖，并在返回上下文中保存该值

#### Scenario: Reuse reference time for one request

- **WHEN** 同一请求执行 Rewrite、Extract 或结构化输出修复重试
- **THEN** 所有阶段使用同一个会话 `reference_time`，不因节点切换或重试重新生成
