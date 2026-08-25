## Purpose

为外部客户端提供稳定的 InOrder 工作流进度流，使调用方能够通过标准 SSE 事件观察意图识别、订单解析和上下文更新的阶段，并可靠获得最终结果或错误。

## ADDED Requirements

### Requirement: Provide an SSE chat endpoint

系统 SHALL 提供 `POST /api/v2/chat` 接口，并在请求协商 `Accept: text/event-stream` 时以 `text/event-stream` 返回工作流事件。

#### Scenario: Accept a chat request
- **WHEN** 客户端提交包含 `session_id`、`message`、可选 `history`、可选 `order_context` 和可选 `reference_time` 的 JSON 请求
- **THEN** 系统使用这些字段执行一次 full 工作流，并返回可被 SSE 客户端逐帧消费的响应

#### Scenario: Reject an invalid request
- **WHEN** 请求缺少非空 `message` 或请求体字段类型不符合接口约定
- **THEN** 系统返回明确的 4xx 错误，不启动 LangGraph 工作流

### Requirement: Emit a stable SSE frame format

系统 SHALL 将每个业务事件编码为一个独立 SSE 数据帧，数据内容为 JSON 对象，且至少包含字符串字段 `type` 和对象字段 `payload`。

#### Scenario: Encode a workflow event
- **WHEN** 工作流发布一个阶段事件
- **THEN** 响应发送形如 `data: {"type":"<EVENT_TYPE>","payload":{...}}\n\n` 的 SSE 帧

#### Scenario: Complete a stream
- **WHEN** 工作流正常完成
- **THEN** 系统发送一个 `DONE` 事件并结束响应，不再发送业务事件

### Requirement: Emit order workflow lifecycle events

订单主意图进入订单子图时，系统 SHALL 按可预测顺序发送 `THINKING_START`、若干 `THINKING_STEP`、`CREATE_ORDER_CONTEXT`、`THINKING_DONE` 和 `DONE`；`THINKING_STEP` 的标题 SHALL 对应当前公开工作流阶段。

#### Scenario: Stream an order workflow
- **WHEN** 主意图识别结果为 `order`
- **THEN** 事件依次覆盖识别用户意图、重写订单语义、提取订单实体、更新订单上下文、生成货物画像（若启用）和处理车型（若启用），随后发送更新后的订单上下文、思考完成和终态事件

#### Scenario: Stream a minimal order workflow
- **WHEN** 订单子图未启用货物画像或车型处理节点
- **THEN** 系统只发送实际执行阶段对应的 `THINKING_STEP`，不发送虚假的阶段事件

### Requirement: Stream the QA terminal branch

问答主意图 SHALL 使用短生命周期事件序列，不得进入订单子图。

#### Scenario: Stream a QA workflow
- **WHEN** 主意图识别结果为 `qa`
- **THEN** 系统发送 `THINKING_START`、表示意图识别的 `THINKING_STEP`、`THINKING_DONE` 和 `DONE`，且不发送 `CREATE_ORDER_CONTEXT`

### Requirement: Publish the updated order context

订单上下文更新成功后，系统 SHALL 发送一个 `CREATE_ORDER_CONTEXT` 事件，其 `payload` SHALL 包含当前可持久化的 `OrderContext` 快照，而不是原始 LLM 响应。

#### Scenario: Context update succeeds
- **WHEN** 订单子图完成上下文合并并产生新的订单上下文
- **THEN** `CREATE_ORDER_CONTEXT.payload` 包含更新后的结构化订单字段和会话标识（若请求提供）

#### Scenario: No context update
- **WHEN** 订单链路没有产生可保存的上下文变化
- **THEN** 系统不发送伪造的上下文创建事件，但仍发送后续生命周期事件

### Requirement: Protect internal model data

SSE 事件 SHALL 只暴露面向客户端的阶段摘要、结构化业务结果和归一化错误，不得暴露完整 prompt、原始模型响应、内部调试堆栈或隐藏思维内容。

#### Scenario: Emit a thinking step
- **WHEN** 系统发送 `THINKING_STEP`
- **THEN** payload 只包含安全的阶段标题、简短进度说明、阶段序号和必要的公开意图信息

#### Scenario: Model returns hidden or verbose content
- **WHEN** LLM 响应包含原始推理、prompt 或供应商调试字段
- **THEN** 这些内容不会出现在任何 SSE 事件 payload 中

### Requirement: Normalize workflow errors

工作流异常 SHALL 被转换为单个 `ERROR` SSE 事件，事件 payload SHALL 包含稳定的错误码和面向客户端的消息；发生错误后系统 SHALL 结束流且不得发送 `DONE`。

#### Scenario: Child graph fails
- **WHEN** 意图子图或订单子图抛出结构化业务错误
- **THEN** 系统发送 `ERROR`，保留可诊断的错误码和阶段信息，不发送部分成功订单结果

#### Scenario: Upstream failure
- **WHEN** LLM 网关、认证、超时或上游服务导致工作流失败
- **THEN** 系统发送归一化的 `ERROR` 事件并关闭 SSE 连接，不泄露上游堆栈

### Requirement: Handle client disconnects

客户端断开 SSE 连接后，系统 SHALL 停止向该客户端发布事件，并释放本次请求关联的工作流资源。

#### Scenario: Client disconnects during execution
- **WHEN** 客户端在工作流尚未完成时断开连接
- **THEN** 系统取消或停止本次事件消费，避免继续向已关闭连接写入数据，并记录可观测的取消状态
