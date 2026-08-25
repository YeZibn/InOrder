## Why

当前 Python 侧已有 LLM 调用重试，但传输错误、结构化输出错误、节点执行错误和整条工作流超时没有形成清晰边界，容易出现重复重试或请求耗时不可控。需要建立只作用于单次 Python 请求的分层策略，同时明确 Python 不负责 Java 侧的会话、业务幂等和整条请求重试。

## What Changes

- 明确 LLM 传输层的可重试错误、次数、退避和超时规则。
- 为结构化 LLM 输出增加有限的格式修复重试，区别于传输重试。
- 定义节点级重试策略，默认不重复执行节点，仅对明确的临时依赖异常允许有限重试。
- 增加 Python 工作流级总超时预算，超时后发送终态 `ERROR` 并结束 SSE。
- 增强错误分类和 SSE 错误 payload，提供阶段、稳定错误码和是否可重试信息。
- 明确 Python 单次请求无状态，不实现跨请求幂等、session 持久化或整图自动重试。

## Capabilities

### New Capabilities

- `python-retry-timeout-policies`: 定义 Python 订单解析请求的分层重试、超时和错误行为。

### Modified Capabilities

- `llm-client`: 补充传输重试、结构化输出错误和超时边界。
- `workflow-sse-events`: 补充工作流超时、可重试错误和一次性请求约束。

## Impact

- 影响 LLM client/resolver、LangGraph 工作流入口、SSE 错误事件和配置项。
- 可能新增工作流总超时配置，不新增外部存储依赖。
- 不修改 Java 服务，不承担 session 持久化、业务幂等或跨请求恢复。
