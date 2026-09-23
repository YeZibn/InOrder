## MODIFIED Requirements

### Requirement: Bound Python request execution

Python 服务 SHALL 为一次完整工作流设置总超时预算；该预算从有效请求准备入场时开始，涵盖入场等待、节点执行、上游请求及应用重试等待。流开始后预算耗尽 SHALL 停止启动后续节点、发送一个终态 `ERROR` 并结束 SSE；流开始前入场等待耗尽 SHALL 按工作流超载拒绝请求。同步依赖若不能被强制中断，SHALL 有有限的单次调用超时并继续计入容量直到实际结束。

#### Scenario: Workflow exceeds its deadline
- **WHEN** SSE 已开始且 LangGraph 工作流执行时间超过配置的总超时预算
- **THEN** 系统发送稳定错误码 `WORKFLOW_TIMEOUT`、当前阶段和 `retryable=false`，且不发送 `DONE`

#### Scenario: Optional stage cannot start within budget
- **WHEN** 工作流剩余时间不足以安全执行货物画像或车型阶段
- **THEN** 系统结束请求并返回超时错误，不在预算耗尽后启动新的 LLM 调用

#### Scenario: Admission consumes the remaining budget
- **WHEN** 请求在等待工作流入场期间耗尽本次预算，且 SSE 尚未开始
- **THEN** 系统返回 HTTP 503、`WORKFLOW_OVERLOADED`，不启动 LangGraph 工作流

#### Scenario: Retry cannot fit within remaining budget
- **WHEN** 一次可重试的 LLM 错误发生，但工作流预算已耗尽，或有效 `Retry-After` 的等待将耗尽预算
- **THEN** 系统停止重试并返回工作流超时错误，不继续发起上游请求

### Requirement: Separate retry layers

系统 SHALL 区分 LLM 传输重试、结构化输出修复和节点级重试；一次逻辑传输调用的实际请求次数 SHALL 只受应用层配置的传输重试次数控制，不得被 SDK 内部默认重试再次放大。所有重试及修复调用 SHALL 共享同一工作流剩余预算；一层已经处理的失败不得被另一层无条件重复放大。

#### Scenario: Retry a transient LLM transport failure
- **WHEN** 单次模型调用遇到超时、限流或 5xx 网关错误
- **THEN** LLM 层在次数、退避及剩余时间上限内重试，成功后节点只返回一次结果

#### Scenario: Do not retry fatal LLM errors
- **WHEN** 模型调用返回鉴权、配置、参数或模型不存在错误
- **THEN** 系统不重试并返回归一化错误

#### Scenario: Repair malformed structured output once
- **WHEN** 模型请求成功但返回空内容、非法 JSON 或不符合结构约束的结果
- **THEN** 对应 resolver 在剩余预算允许时最多执行一次格式修复请求，仍失败则结束当前节点

#### Scenario: Avoid default node replay
- **WHEN** 节点因已归一化的 LLM 失败而结束
- **THEN** 系统不得再默认重复执行整个节点；只有明确标记为临时依赖错误的节点才允许有限节点重试

#### Scenario: No nested transport retries
- **WHEN** 应用层配置某次逻辑 LLM 调用最多重试两次，且每次尝试都遇到可重试故障
- **THEN** 该逻辑调用最多发出三次实际上游请求，而不是由 SDK 再次放大
