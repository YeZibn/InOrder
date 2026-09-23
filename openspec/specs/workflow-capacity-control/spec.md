# workflow-capacity-control Specification

## Purpose

为单个 Python API worker 的工作流及其模型依赖设置可配置的并发和等待边界，使服务在流量高于处理能力时及时拒绝新请求，并在取消或失败后准确释放容量。

## Requirements

### Requirement: Bound workflow admission

系统 SHALL 限制每个 API worker 同时执行的工作流数量、等待入场的请求数量和最长等待时间。输入校验成功后，系统 SHALL 在开始 SSE 响应前完成工作流入场；容量满且无法在有限等待内入场时 SHALL 返回 HTTP 503 和稳定的 `WORKFLOW_OVERLOADED` 错误码，不启动工作流或发送 SSE 帧。

#### Scenario: Admit within capacity
- **WHEN** 有可用工作流容量，且客户端提交有效请求
- **THEN** 系统接纳请求并按既有协议发送 SSE 工作流事件

#### Scenario: Reject a full queue
- **WHEN** 工作流执行容量与等待队列均已满，客户端提交有效请求
- **THEN** 系统立即返回 HTTP 503、`WORKFLOW_OVERLOADED` 错误码，不发出 `THINKING_START`

#### Scenario: Waiting time expires
- **WHEN** 请求已进入等待队列，但在配置的等待时限或本次请求剩余预算内仍未获得工作流容量
- **THEN** 系统在 SSE 开始前返回 HTTP 503、`WORKFLOW_OVERLOADED` 错误码，并移除该等待请求

### Requirement: Bound LLM and synchronous extractor work

系统 SHALL 分别限制 API 工作流内的异步 LLM 调用并发量和同步 LangExtract 执行线程数。等待依赖容量 SHALL 有限且受工作流剩余时间约束；若依赖等待时限先到，系统 SHALL 发送单个可重试的 `WORKFLOW_OVERLOADED` `ERROR` 事件；若工作流 deadline 先到，系统 SHALL 发送 `WORKFLOW_TIMEOUT`。两种情况均结束流且不发送 `DONE`。

#### Scenario: LLM capacity is exhausted during a stream
- **WHEN** 工作流已开始，LLM 调用未在依赖等待时限内取得容量，且工作流 deadline 尚未到达
- **THEN** 系统发送一个 `WORKFLOW_OVERLOADED` `ERROR` 事件并结束当前 SSE 流

#### Scenario: LangExtract capacity is exhausted during a stream
- **WHEN** 工作流已开始，LangExtract 执行未在依赖等待时限内取得线程容量，且工作流 deadline 尚未到达
- **THEN** 系统发送一个 `WORKFLOW_OVERLOADED` `ERROR` 事件，并且不启动额外的提取线程

### Requirement: Release capacity after actual work ends

系统 SHALL 在正常完成、失败和客户端断开后释放已占用的工作流与依赖容量；同步工作即使无法立即停止，也 SHALL 继续计入其并发上限直到实际退出。容量限制 SHALL 有有限且可验证的运行时配置，非法配置 SHALL 在服务启动时失败。

#### Scenario: Client disconnects while synchronous extraction is running
- **WHEN** 客户端断开连接而 LangExtract 线程尚未结束
- **THEN** 系统停止向该客户端发布事件，且该线程在实际结束前仍占用 LangExtract 容量

#### Scenario: Invalid capacity configuration
- **WHEN** 并发上限、等待队列上限或等待时限配置为非法值
- **THEN** 服务在接收请求前返回配置错误，不以无限制容量启动
