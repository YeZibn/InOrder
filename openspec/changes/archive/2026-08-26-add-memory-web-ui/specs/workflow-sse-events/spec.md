## MODIFIED Requirements

### Requirement: Provide an SSE chat endpoint

系统 SHALL 提供 `POST /api/v2/chat` 接口，并在请求协商 `Accept: text/event-stream` 时以 `text/event-stream` 返回工作流事件；同时 SHALL 在 API 服务根路径提供本地测试页面，该页面使用同源请求调用该接口。现有请求字段、事件格式和工作流行为保持不变。

#### Scenario: Accept a chat request

- **WHEN** 客户端提交包含 `session_id`、`message`、可选 `history`、可选 `order_context` 和可选 `reference_time` 的 JSON 请求
- **THEN** 系统使用这些字段执行一次 full 工作流，并返回可被 SSE 客户端逐帧消费的响应

#### Scenario: Open same-origin test page

- **WHEN** 用户访问 API 服务根路径 `/`
- **THEN** 系统返回本地测试页面，页面可以同源调用 `/api/v2/chat`，无需额外 CORS 配置

#### Scenario: Adapt events to user-facing progress

- **WHEN** 同源测试页面接收到公开 SSE 事件
- **THEN** 页面按事件到达顺序实时转换为用户可理解的进度小提示，并保持现有 SSE 事件协议不变；技术事件名和内部节点名不直接呈现给用户

#### Scenario: Reject an invalid request

- **WHEN** 请求缺少非空 `message` 或请求体字段类型不符合接口约定
- **THEN** 系统返回明确的 4xx 错误，不启动 LangGraph 工作流
