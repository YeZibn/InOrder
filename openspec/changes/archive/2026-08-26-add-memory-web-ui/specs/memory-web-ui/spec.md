## Purpose

为 InOrder 提供一个无需前端构建和外部持久化的浏览器测试界面，用于验证 SSE 工作流阶段展示及多轮订单上下文传递。

## ADDED Requirements

### Requirement: Provide an in-memory workflow test page

系统 SHALL 在 API 服务根路径提供可访问的 InOrder 测试页面。页面 SHALL 允许用户输入消息、触发一次工作流请求并展示当前会话的消息列表。

#### Scenario: Open test page

- **WHEN** 用户访问 API 服务根路径 `/`
- **THEN** 系统返回可在现代浏览器直接运行的测试页面，不要求 Node.js 或前端构建步骤

#### Scenario: Send a message

- **WHEN** 用户输入非空消息并点击发送
- **THEN** 页面向 `/api/v2/chat` 发送包含 `session_id`、`message`、`history` 和 `order_context` 的 JSON 请求

#### Scenario: Reject empty message locally

- **WHEN** 用户未输入消息并尝试发送
- **THEN** 页面不发起网络请求，并提示用户输入消息

### Requirement: Consume and display SSE workflow events

页面 SHALL 使用 POST 请求消费 `/api/v2/chat` 的 SSE 流，并按到达顺序展示公开工作流事件，不暴露 prompt、原始模型响应或内部堆栈。

#### Scenario: Display workflow stages

- **WHEN** 服务端发送 `THINKING_START` 或 `THINKING_STEP`
- **THEN** 页面在当前消息的处理中区域显示阶段标题和进度

### Requirement: Show friendly real-time progress hints

页面 SHALL 在 SSE 事件到达后立即将技术事件适配为面向用户的简短、友好的处理提示。页面 SHALL 维护当前处理中提示和已完成提示的可读记录，不得直接向用户展示 `THINKING_START`、`THINKING_STEP`、内部节点名或完整 SSE JSON。

#### Scenario: Start processing hint

- **WHEN** 服务端发送 `THINKING_START`
- **THEN** 页面立即显示“正在理解您的需求…”或语义等价的开始处理提示

#### Scenario: Stage-specific hints

- **WHEN** 服务端发送带有 `stage` 的 `THINKING_STEP`
- **THEN** 页面根据公开阶段显示对应的用户提示，例如意图阶段显示“正在识别您的运输需求…”，订单阶段显示“正在整理订单信息…”，货物画像阶段显示“正在分析货物特征…”，车型阶段显示“正在匹配合适车型…”

#### Scenario: Context update hint

- **WHEN** 服务端发送 `CREATE_ORDER_CONTEXT`
- **THEN** 页面显示“订单信息已更新”或语义等价提示，并同步刷新上下文面板

#### Scenario: Finish processing hint

- **WHEN** 服务端发送 `THINKING_DONE` 或 `DONE`
- **THEN** 页面显示“处理完成”提示；收到 `DONE` 后再展示最终结构化结果

#### Scenario: Error hint

- **WHEN** 服务端发送 `ERROR`
- **THEN** 页面将错误 payload 适配为简明错误提示、结束加载状态，并不显示成功完成提示

#### Scenario: Display context update

- **WHEN** 服务端发送 `CREATE_ORDER_CONTEXT`
- **THEN** 页面更新内存中的 `order_context`，并刷新上下文 JSON 视图

#### Scenario: Display terminal result

- **WHEN** 服务端发送 `DONE`
- **THEN** 页面展示安全的最终结构化结果并结束当前消息的加载状态

#### Scenario: Display normalized error

- **WHEN** 服务端发送 `ERROR`
- **THEN** 页面展示错误消息和阶段，并结束当前消息的加载状态，不伪造成功结果

### Requirement: Preserve multi-turn state in browser memory

页面 SHALL 在当前页面生命周期内保存 `history`、完整 `order_context`、`reference_time` 和 `session_id`，并在下一次请求中复用；刷新或关闭页面后允许丢失这些数据。

#### Scenario: Continue a conversation

- **WHEN** 第一轮请求返回订单上下文后用户发送第二轮消息
- **THEN** 第二轮请求携带上一轮最新的 `history` 和 `order_context`，包括已保存的 `reference_time`

#### Scenario: Keep concise assistant history

- **WHEN** 一轮工作流正常完成
- **THEN** 页面向内存 history 追加用户消息和精简 assistant 摘要，不将完整 SSE JSON 写入对话历史

#### Scenario: Clear in-memory session

- **WHEN** 用户点击清空会话
- **THEN** 页面清空消息、history 和 order_context，并恢复默认 session 标识

### Requirement: Inspect current session state

页面 SHALL 提供查看当前 `order_context` 和 `history` 的调试区域。

#### Scenario: Inspect order context

- **WHEN** 用户查看订单上下文面板
- **THEN** 页面展示当前可序列化的完整 `order_context` JSON

#### Scenario: Inspect conversation history

- **WHEN** 用户查看历史面板
- **THEN** 页面展示当前内存中的有序 turns JSON
