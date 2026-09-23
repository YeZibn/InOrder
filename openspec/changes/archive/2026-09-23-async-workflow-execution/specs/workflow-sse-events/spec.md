## ADDED Requirements

### Requirement: Keep concurrent SSE workflows responsive

系统 SHALL 在一个工作流等待上游 I/O 或执行同步节点时，继续处理同一 API worker 的其他请求。异步执行 SHALL 保持现有节点完成进度、事件顺序、终态字段和安全过滤语义；本接口不得将模型 token 增量作为新的 SSE 事件交付。

#### Scenario: Another request progresses while one model call is slow
- **WHEN** 请求 A 的工作流正在等待慢速模型调用，同时请求 B 到达同一 API worker 且已获入场容量
- **THEN** 请求 B 能继续处理并发送其事件，不必等待请求 A 的模型调用结束

#### Scenario: Preserve node-level progress
- **WHEN** 异步执行的订单子图依次完成多个节点
- **THEN** 客户端按实际完成顺序收到既有 `THINKING_STEP` 节点事件以及原有终态结果，不收到模型 token 事件

## MODIFIED Requirements

### Requirement: Handle client disconnects

客户端断开 SSE 连接或请求被取消后，系统 SHALL 停止向该客户端发布事件，停止继续调度尚未开始的工作流步骤，并释放本次请求资源；不可强制中断的同步工作须在退出前继续受到并发限制。系统不得在 Python 服务内保存或恢复未完成工作流，且不得因取消再发送 `ERROR` 或 `DONE`。

#### Scenario: Disconnect during execution
- **WHEN** 客户端在工作流尚未完成时断开连接
- **THEN** 系统停止后续事件消费，不再向该客户端发送终态事件；后续是否重新发起请求由调用方决定

#### Scenario: Cancel while a synchronous dependency is still running
- **WHEN** 请求取消时某个同步依赖无法即时停止
- **THEN** 系统不继续启动后续节点，已启动的同步工作在实际结束前保持受限，且不向断开的客户端发送 `ERROR` 或 `DONE`
