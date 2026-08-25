## Context

Python 服务接收 Java 传入的完整 `message`、`history` 和 `order_context`，每次请求独立执行 LangGraph 并通过 SSE 返回结果。现有 `LLMClient` 已实现基础传输重试，但 resolver、节点和工作流边界尚未统一。

## Goals / Non-Goals

**Goals:**

- 分离传输重试、结构化输出修复、节点策略和工作流总超时。
- 使一次 Python 请求有明确的时间预算和终态错误。
- 保持 SSE 业务阶段稳定，不向客户端暴露内部重试过程。
- 保持 Python 无状态，Java 侧会话与业务重试不纳入本 change。

**Non-Goals:**

- 不实现跨请求幂等或任务恢复。
- 不自动重放整个 MainGraph。
- 不把每次内部重试作为 SSE 事件。

## Decisions

1. **传输重试保留在 LLMClient。** 超时、429、网络错误和 5xx 在有限次数内指数退避；4xx 鉴权和配置错误不重试。

2. **格式修复放在 resolver。** 请求已成功但结构化结果不合法时，最多一次修复请求；不让底层传输层感知业务 schema。

3. **节点默认不重试。** 确定性节点不重试；只有明确标记为临时依赖错误的节点才允许一次节点级重试，且共享同一工作流 deadline。

4. **工作流使用总 deadline。** 每个节点和 LLM 调用都必须受剩余预算约束；预算耗尽立即结束并发送 `WORKFLOW_TIMEOUT`。

5. **错误事件带 retryable。** 客户端只获得稳定错误码、阶段和是否可重试，不获得堆栈或供应商细节。

## Risks / Trade-offs

- [Risk] 总 deadline 过短可能导致可选画像或车型阶段未执行 → Mitigation: 配置合理默认值并在日志记录剩余预算。
- [Risk] 节点级重试与 LLM 重试叠加造成调用放大 → Mitigation: 默认关闭节点重试并设置全局调用预算。
- [Risk] SSE 断开后底层调用仍短暂运行 → Mitigation: 检查断连、停止发布，并在可用时取消底层任务。
