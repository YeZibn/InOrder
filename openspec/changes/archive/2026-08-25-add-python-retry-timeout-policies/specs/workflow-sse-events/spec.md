## MODIFIED Requirements

### Requirement: Normalize workflow errors

工作流异常 SHALL 被转换为单个 `ERROR` SSE 事件，事件 payload SHALL 包含稳定错误码、公开阶段和 `retryable` 布尔值；发生错误后系统 SHALL 结束流且不得发送 `DONE`。

#### Scenario: Retryable upstream failure
- **WHEN** LLM 网关、认证、超时或上游服务导致工作流失败
- **THEN** 系统发送归一化的 `ERROR` 事件，标明当前阶段和是否可重试，不泄露上游堆栈

#### Scenario: Workflow timeout
- **WHEN** 工作流超过 Python 服务配置的总执行预算
- **THEN** 系统发送 `WORKFLOW_TIMEOUT` 错误并关闭 SSE，不发送 `DONE`

### Requirement: Handle client disconnects

客户端断开 SSE 连接后，系统 SHALL 停止向该客户端发布事件，释放本次请求资源，且不得在 Python 服务内保存或恢复未完成工作流。

#### Scenario: Disconnect during execution
- **WHEN** 客户端在工作流尚未完成时断开连接
- **THEN** 系统停止后续事件消费；后续是否重新发起请求由调用方决定
