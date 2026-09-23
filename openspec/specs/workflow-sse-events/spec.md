# workflow-sse-events Specification

## Purpose

为外部客户端提供稳定的 InOrder 工作流进度流，使调用方能够通过标准 SSE 事件观察意图识别、订单解析和上下文更新的阶段，并可靠获得最终订单上下文或错误。
## Requirements
### Requirement: Provide an SSE chat endpoint

系统 SHALL 提供 `POST /api/v2/chat` 接口，并在请求协商 `Accept: text/event-stream` 时以 `text/event-stream` 返回工作流事件；同时 SHALL 在 API 服务根路径提供本地测试页面，该页面使用同源请求调用该接口。Python SHALL 从请求中的 `order_context.reference_time`、请求级 `reference_time` 或当前 `Asia/Shanghai` 时间按优先级确定一个会话时间锚点，将其写入工作流 state，并在更新后的 `OrderContext` 快照中返回。

#### Scenario: Accept a chat request
- **WHEN** 客户端提交包含 `session_id`、`message`、可选 `history`、可选 `order_context` 和可选 `reference_time` 的 JSON 请求
- **THEN** 系统使用这些字段执行一次 full 工作流，并返回可被 SSE 客户端逐帧消费的响应

#### Scenario: Reject an invalid request
- **WHEN** 请求缺少非空 `message` 或请求体字段类型不符合接口约定
- **THEN** 系统返回明确的 4xx 错误，不启动 LangGraph 工作流

#### Scenario: Open same-origin test page
- **WHEN** 用户访问 API 服务根路径 `/`
- **THEN** 系统返回本地测试页面，页面可以同源调用 `/api/v2/chat`，无需额外 CORS 配置

#### Scenario: Adapt events to user-facing progress
- **WHEN** 同源测试页面接收到公开 SSE 事件
- **THEN** 页面按事件到达顺序实时转换为用户可理解的进度小提示，并保持现有 SSE 事件协议不变；技术事件名和内部节点名不直接呈现给用户

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
- **THEN** 所有阶段使用同一个 reference_time，不因节点切换或重试重新生成

### Requirement: Emit a stable SSE frame format

系统 SHALL 将每个业务事件编码为一个独立 SSE 数据帧，数据内容为 JSON 对象，且至少包含字符串字段 `type` 和对象字段 `payload`。正常完成订单工作流时，`DONE.payload.result` SHALL 包含结构化订单摘要、面向用户的自然语言回复及完整性状态，同时继续提供客户端兼容所需的结构化业务结果。

#### Scenario: Encode a workflow event
- **WHEN** 工作流发布一个阶段事件
- **THEN** 响应发送形如 `data: {"type":"<EVENT_TYPE>","payload":{...}}\n\n` 的 SSE 帧

#### Scenario: Complete a stream
- **WHEN** 工作流正常完成
- **THEN** 系统发送一个 `DONE` 事件并结束响应，不再发送业务事件

#### Scenario: Complete an order stream with summary
- **WHEN** 订单工作流正常完成
- **THEN** 系统发送一个 `DONE` 事件，其结果包含可直接展示给用户的自然语言回复、结构化状态及缺失字段信息，并结束响应；客户端 SHALL 将自然语言回复追加到主对话框的助手消息列表，同时可更新右侧摘要面板，不直接渲染原始 JSON 或内部状态字段

#### Scenario: Show the final summary in the main conversation
- **WHEN** Web 客户端收到包含订单摘要的 `DONE` 事件
- **THEN** 客户端从 `order_result.order_summary.user_message`（兼容顶层 `order_summary.user_message`）读取文案，并在主对话框追加一条助手消息；同一 `DONE` 事件不得重复追加消息

#### Scenario: Preserve compatibility for responses without an order summary
- **WHEN** Web 客户端收到非订单结果或不包含 `order_summary.user_message` 的兼容 `DONE` 事件
- **THEN** 客户端不追加订单摘要助手消息，继续按既有方式展示普通完成状态和结构化结果

### Requirement: Emit order workflow lifecycle events

订单主意图进入订单子图时，系统 SHALL 对外发送识别用户意图、处理订单、生成货物画像（若执行）和处理车型（若执行）等公开业务阶段，并可在这些阶段内按子图节点完成发送更细粒度的 `THINKING_STEP`。节点事件必须按实际完成顺序出现；不得暴露 prompt、原始模型响应或内部思维。既有 `THINKING_START`、`THINKING_DONE`、`DONE` 和上下文事件语义保持不变。

#### Scenario: Stream an order workflow with optional stages

- **WHEN** 主意图识别结果为 `order` 且订单子图执行多个节点
- **THEN** 事件依次包含开始事件、意图子图及订单子图已完成节点对应的 `THINKING_STEP`，随后发送实际执行阶段的上下文更新（若有）、思考完成和终态事件

#### Scenario: Publish each completed node once

- **WHEN** 子图节点完成并返回状态更新
- **THEN** 系统发送一个对应的节点完成进度事件，事件包含递增 `sequence`，同一节点不得因父图聚合再次重复发送

#### Scenario: Hide order implementation details

- **WHEN** 订单子图执行 rewrite、extract、update_context 或其他内部节点
- **THEN** SSE 可以用稳定节点标识支持客户端映射，但不得把内部调试信息、模型输出或隐藏思维放入 payload

#### Scenario: Stream a minimal order workflow

- **WHEN** 订单子图未启用货物画像或车型处理节点
- **THEN** 系统只发送实际执行的节点和公开阶段事件，不发送虚假的可选节点事件

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

工作流异常 SHALL 被转换为单个 `ERROR` SSE 事件，事件 payload SHALL 包含稳定错误码、公开阶段和 `retryable` 布尔值；发生错误后系统 SHALL 结束流且不得发送 `DONE`。

#### Scenario: Retryable upstream failure
- **WHEN** LLM 网关、认证、超时或上游服务导致工作流失败
- **THEN** 系统发送归一化的 `ERROR` 事件，标明当前阶段和是否可重试，不泄露上游堆栈

#### Scenario: Workflow timeout
- **WHEN** 工作流超过 Python 服务配置的总执行预算
- **THEN** 系统发送 `WORKFLOW_TIMEOUT` 错误并关闭 SSE，不发送 `DONE`

### Requirement: Return conversation recovery state

成功结束时 `DONE` 事件 SHALL 返回规范化的会话 `history` 或等价 `history_patch`；发生 `ERROR` 或客户端断开时不得伪造 assistant 内容，调用方可保留 pending user 回合并重试。历史快照中 assistant turn 的内容 SHALL 来自订单工作流的最终总结（`order_summary.user_message`），且服务端在消费结构化结果时 SHALL 对带 `to_dict()` 的领域对象先做字典化转换后再取字段。

#### Scenario: DONE includes recovered history
- **WHEN** 工作流成功处理包含 pending user 回合的请求
- **THEN** DONE payload 包含无重复消息的可持久化 history 或 history_patch

#### Scenario: Assistant turn carries order summary
- **WHEN** 订单子图执行完成且 `order_summary` 在结果中为 dataclass 对象（非 dict）
- **THEN** 历史 assistant turn 内容为该对象的 `user_message` 字段值，而非意图兜底文案

#### Scenario: No order summary falls back to intent
- **WHEN** 结果中不存在可提取的订单总结（如仅意图分类或 QA 分支）
- **THEN** assistant turn 使用意图摘要素材；完全无可提取内容时才使用简短兜底文案

#### Scenario: ERROR preserves pending state
- **WHEN** 工作流在 DONE 前失败
- **THEN** ERROR payload 不包含 assistant 摘要，客户端可继续使用原 pending history

### Requirement: Keep concurrent SSE workflows responsive

系统 SHALL 在一个工作流等待上游 I/O 或执行同步节点时，继续处理同一 API worker 的其他请求。异步执行 SHALL 保持现有节点完成进度、事件顺序、终态字段和安全过滤语义；本接口不得将模型 token 增量作为新的 SSE 事件交付。

#### Scenario: Another request progresses while one model call is slow
- **WHEN** 请求 A 的工作流正在等待慢速模型调用，同时请求 B 到达同一 API worker 且已获入场容量
- **THEN** 请求 B 能继续处理并发送其事件，不必等待请求 A 的模型调用结束

#### Scenario: Preserve node-level progress
- **WHEN** 异步执行的订单子图依次完成多个节点
- **THEN** 客户端按实际完成顺序收到既有 `THINKING_STEP` 节点事件以及原有终态结果，不收到模型 token 事件

### Requirement: Handle client disconnects

客户端断开 SSE 连接或请求被取消后，系统 SHALL 停止向该客户端发布事件，停止继续调度尚未开始的工作流步骤，并释放本次请求资源；不可强制中断的同步工作须在退出前继续受到并发限制。系统不得在 Python 服务内保存或恢复未完成工作流，且不得因取消再发送 `ERROR` 或 `DONE`。

#### Scenario: Disconnect during execution
- **WHEN** 客户端在工作流尚未完成时断开连接
- **THEN** 系统停止后续事件消费，不再向该客户端发送终态事件；后续是否重新发起请求由调用方决定

#### Scenario: Cancel while a synchronous dependency is still running
- **WHEN** 请求取消时某个同步依赖无法即时停止
- **THEN** 系统不继续启动后续节点，已启动的同步工作在实际结束前保持受限，且不向断开的客户端发送 `ERROR` 或 `DONE`
