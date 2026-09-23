## 1. 容量与同步节点边界

- [x] 1.1 增加并校验每 worker 的工作流并发、等待队列、等待时限、LLM 并发及 LangExtract 线程配置，使用设计中的有限默认值。
- [x] 1.2 实现响应头发送前的工作流入场与有界等待；队列满或等待到期时返回 503 JSON `WORKFLOW_OVERLOADED`，并覆盖等待期间断开及 deadline 耗尽。
- [x] 1.3 为尚未迁移的同步图节点建立通用有界 executor，为 LangExtract 建立专用线程池；取消等待后仍按底层 future 的实际完成时间释放线程容量，并在应用关闭时清理线程池。
- [x] 1.4 建立共享 LLM 容量和流内依赖等待边界，配置 `WORKFLOW_OVERLOADED` 的安全 SSE 错误映射与 `retryable` 值。

## 2. 异步 SSE 工作流

- [x] 2.1 给 `WorkflowEventAdapter` 增加基于 `graph.astream(..., subgraphs=True, version="v2")` 的异步事件迭代，复用现有子图更新解析、结果组装及事件去重逻辑。
- [x] 2.2 将图节点接入同步/异步双入口 runnable；API 的异步路径按节点提交同步工作，CLI 的同步图调用保持可用。
- [x] 2.3 FastAPI 使用 `async for` 消费异步适配器，保证入场槽位在响应完成、错误、开始前断开及取消后释放；移除 API 路径的同步图 fallback。
- [x] 2.4 修正异步 API/适配器对取消的处理，断开后不发送 `ERROR`/`DONE`，并在流内 deadline 到期时只发一个 `WORKFLOW_TIMEOUT` 终态。
- [x] 2.5 用慢速同步节点和并发请求验证事件循环仍可响应，且节点进度顺序、最终结果、history 恢复与原 SSE 协议一致。

## 3. 原生异步模型调用与重试

- [x] 3.1 为 Chat Completions 和 Responses 增加 `AsyncOpenAI` transport，按现有配置支持完整响应及模型流式输入；同步与异步 SDK 客户端均关闭默认重试，并在应用关闭时清理异步客户端。
- [x] 3.2 为 `LLMClient` 增加异步完整调用、异步模型流消费及非阻塞重试；复用同步路径的响应归一化、错误分类和流式内容交付边界。
- [x] 3.3 将 `deadline_at` 从图 state 传入异步模型、格式修复和客户端；按剩余时间限制每次请求及退避，解析并遵守可执行的 `Retry-After`。
- [x] 3.4 为意图、重写、JSON 实体提取及货物画像模型和相关图节点增加原生异步入口；同步 CLI 仍走现有调用入口。
- [x] 3.5 配置并验证 LangExtract 独立 provider 的有限 timeout、零 SDK retry 和内部并行度 1；提取调用同时占用共享 LLM 与专用线程容量。
- [x] 3.6 用模拟上游验证单次逻辑 LLM 调用的实际上游请求次数、fatal 错误不重试、格式修复次数、两种 API 模式及截止时间前后的行为。

## 4. 集成验证与交付

- [x] 4.1 验证满队列在 SSE 前返回 503、流内依赖超载只发一个 `ERROR`，并在断开及同步工作滞留时检查容量不提前释放。
- [x] 4.2 运行现有业务、CLI、SSE 与 Python 测试；验证 LangGraph 当前版本及依赖范围内最低受支持版本的异步节点和子图更新行为。
- [x] 4.3 使用目标并发的可重复压测记录事件循环响应、p95、503 比例、线程峰值及上游请求数，并据结果调整有限默认容量与运行说明。
- [x] 4.4 运行 `openspec validate async-workflow-execution --strict`，确认改动范围只涉及本变更且不引入 token 级 SSE 或业务算法变化。
