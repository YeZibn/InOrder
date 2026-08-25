# python-retry-timeout-policies Specification

## Purpose

为无状态 Python 订单解析服务定义清晰、可控且互不重复的重试与超时边界，避免单次请求无限等待或因多层重试造成重复执行。

## Requirements

### Requirement: Bound Python request execution

Python 服务 SHALL 为一次完整工作流设置总超时预算；预算耗尽后 SHALL 停止启动后续节点，发送一个终态 `ERROR` 并结束本次 SSE 请求。

#### Scenario: Workflow exceeds its deadline
- **WHEN** LangGraph 工作流执行时间超过配置的总超时预算
- **THEN** 系统发送稳定错误码 `WORKFLOW_TIMEOUT`、当前阶段和 `retryable=false`，且不发送 `DONE`

#### Scenario: Optional stage cannot start within budget
- **WHEN** 工作流剩余时间不足以安全执行货物画像或车型阶段
- **THEN** 系统结束请求并返回超时错误，不在预算耗尽后启动新的 LLM 调用

### Requirement: Keep Python requests stateless

Python SHALL 将每次请求视为独立执行单元，不根据 `session_id` 或其他标识读取、保存或恢复跨请求状态，也不得自动重放整条工作流。

#### Scenario: Repeat request arrives
- **WHEN** 客户端再次提交相同或不同标识的请求
- **THEN** Python 只使用本次请求提供的 `message`、`history` 和 `order_context` 执行，不进行本地幂等判断

### Requirement: Separate retry layers

系统 SHALL 区分 LLM 传输重试、结构化输出修复和节点级重试；一层已经处理的失败不得被另一层无条件重复放大。

#### Scenario: Retry a transient LLM transport failure
- **WHEN** 单次模型调用遇到超时、限流或 5xx 网关错误
- **THEN** LLM 层在次数和退避上限内重试，成功后节点只返回一次结果

#### Scenario: Do not retry fatal LLM errors
- **WHEN** 模型调用返回鉴权、配置、参数或模型不存在错误
- **THEN** 系统不重试并返回归一化错误

#### Scenario: Repair malformed structured output once
- **WHEN** 模型请求成功但返回空内容、非法 JSON 或不符合结构约束的结果
- **THEN** 对应 resolver 最多执行一次格式修复请求，仍失败则结束当前节点

#### Scenario: Avoid default node replay
- **WHEN** 节点因已归一化的 LLM 失败而结束
- **THEN** 系统不得再默认重复执行整个节点；只有明确标记为临时依赖错误的节点才允许有限节点重试
