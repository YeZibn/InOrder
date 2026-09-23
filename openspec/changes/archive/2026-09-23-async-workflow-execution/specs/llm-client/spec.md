## ADDED Requirements

### Requirement: Provide asynchronous LLM calls alongside synchronous calls

LLM 客户端 SHALL 提供非阻塞的异步完整调用与配置驱动的异步流式调用，覆盖现有 Chat Completions 和 Responses 两种接口模式，并返回与同步入口等价的规范化完整结果。现有同步入口 SHALL 继续可用于 CLI 和其他同步调用方；异步流式调用不改变工作流对外的节点级 SSE 协议。

#### Scenario: Async completion returns normalized result
- **WHEN** 异步工作流调用模型且上游返回成功
- **THEN** 调用方获得与同步入口同形的文本、模型和可用 usage，等待期间事件循环可处理其他请求

#### Scenario: Async model streaming returns a complete result
- **WHEN** 配置启用模型流式调用且异步工作流选择 Chat Completions 或 Responses
- **THEN** 客户端异步消费内容增量并返回完整的规范化结果，不把 token 增量直接发送为工作流 SSE 事件

#### Scenario: Existing synchronous caller remains supported
- **WHEN** CLI 通过现有同步调用入口请求模型
- **THEN** 客户端继续按既有返回类型与错误类型返回结果

## MODIFIED Requirements

### Requirement: Handle transient upstream failures

LLM 客户端 SHALL 仅对网络失败、请求超时、限流和 5xx 上游错误进行有限重试；鉴权、配置、参数和模型不存在错误 SHALL 不重试。一次逻辑调用 SHALL 最多发出配置允许的实际上游请求次数，且异步重试等待不得阻塞事件循环。有效 `Retry-After` SHALL 在剩余时间允许时得到遵守；若等待将超过工作流 deadline，系统 SHALL 停止重试。

#### Scenario: Retry a transient failure
- **WHEN** LLM 请求遇到超时、429 或 5xx 错误
- **THEN** 客户端在配置的次数、退避上限和剩余预算内重试，最终成功则只返回一个规范化响应

#### Scenario: Stop on fatal failure
- **WHEN** LLM 请求遇到 400、401、403 或配置错误
- **THEN** 客户端不重试并返回稳定的应用层错误

#### Scenario: Honor a feasible retry delay
- **WHEN** 上游返回可重试限流错误及有效 `Retry-After`，且等待后仍有工作流预算
- **THEN** 客户端至少等待该时长后再重试，且不超过总重试次数

#### Scenario: Stop retrying at the deadline
- **WHEN** 调用方提供的工作流 deadline 已到达，或计划中的有效 `Retry-After` 等待将越过该 deadline
- **THEN** 客户端不再启动新请求，并向工作流报告超时
