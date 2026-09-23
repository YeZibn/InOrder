## Why

`/api/v2/chat` 在异步 SSE 生成器中同步迭代 LangGraph，节点等待 LLM 时会阻塞 FastAPI 事件循环，使同一 worker 的其他请求和进度事件无法及时处理。现有 SDK 与 `LLMClient` 的重试还可能叠加，且单次调用及排队时间没有被工作流总 deadline 完整约束。

## What Changes

- 将 SSE 适配层改为异步迭代，使用编译图的 `astream()` 保持现有节点级进度及终态事件；同步节点先由受控 executor 承接，随后把 LLM 等 I/O 调用逐步迁移为原生异步。
- 为每个 API worker 设置工作流、LLM 和 LangExtract 的并发容量，以及有界等待队列；工作流入场超载时在 SSE 开始前返回 503，用户级配额限制的 429 不在本次范围。
- 关闭 OpenAI SDK 在 InOrder 自管 LLM 调用链上的隐式重试，由应用统一限制重试次数、退避和工作流剩余时间；审查 LangExtract 独立上游路径的重试及容量。
- 在客户端断开或请求取消时停止事件消费并释放容量；保留现有 `THINKING_*`、上下文、`DONE`、`ERROR` 的节点级 SSE 协议，不增加 token streaming。

## Capabilities

### New Capabilities

- `workflow-capacity-control`: 为 API 工作流及其 LLM、LangExtract 依赖定义有限并发、有限等待和超载响应。

### Modified Capabilities

- `workflow-sse-events`: 保证慢节点运行时其他请求仍可推进，并明确取消、断开及超载时的响应边界，同时维持现有事件语义。
- `python-retry-timeout-policies`: 将等待、每次上游调用和重试纳入工作流总 deadline，避免 SDK 与应用双层重试。
- `llm-client`: 提供适合异步工作流的调用能力，统一控制传输重试并保留同步调用入口。

## Impact

- 主要涉及 FastAPI SSE 入口、`WorkflowEventAdapter`、LangGraph 节点与模型适配器、`LLMClient`/OpenAI-compatible transport、LangExtract 边界及运行时配置。
- `/api/v2/chat` 的有效请求在服务过载时可能收到非 SSE 的 503；客户端需要处理该 HTTP 响应。正常 SSE 帧和业务结果保持兼容。
- CLI 和现有同步调用方继续可用；不引入前端 token 流，也不改变订单或车型的业务计算规则。
