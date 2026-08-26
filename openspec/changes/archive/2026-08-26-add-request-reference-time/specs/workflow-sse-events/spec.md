## MODIFIED Requirements

### Requirement: Provide an SSE chat endpoint

系统 SHALL 提供 `POST /api/v2/chat` 接口，并在请求协商 `Accept: text/event-stream` 时以 `text/event-stream` 返回工作流事件。请求包含有效 `reference_time` 时 SHALL 使用调用方提供的值；未提供时 SHALL 在请求进入 Python 边界时生成当前 `Asia/Shanghai` 时间，并将该值写入本次工作流 state，供所有节点和重试复用。

#### Scenario: Accept a chat request
- **WHEN** 客户端提交包含 `session_id`、`message`、可选 `history`、可选 `order_context` 和可选 `reference_time` 的 JSON 请求
- **THEN** 系统使用这些字段执行一次 full 工作流，确定一个有效 reference_time，并返回可被 SSE 客户端逐帧消费的响应

#### Scenario: Reject an invalid request
- **WHEN** 请求缺少非空 `message` 或请求体字段类型不符合接口约定
- **THEN** 系统返回明确的 4xx 错误，不启动 LangGraph 工作流

#### Scenario: Generate a default reference time
- **WHEN** 客户端未提供 reference_time 或传入空值
- **THEN** Python 在启动工作流前生成当前 Asia/Shanghai 时间，格式为 YYYY-MM-DD HH:MM，不向下游传递空字符串

#### Scenario: Preserve caller-provided reference time
- **WHEN** 客户端提供格式有效的 reference_time
- **THEN** 系统使用该值作为本次工作流的时间锚点，不以本机当前时间覆盖

#### Scenario: Reuse reference time for one request
- **WHEN** 同一请求执行 Rewrite、Extract 或结构化输出修复重试
- **THEN** 所有阶段使用同一个 reference_time，不因节点切换或重试重新生成
