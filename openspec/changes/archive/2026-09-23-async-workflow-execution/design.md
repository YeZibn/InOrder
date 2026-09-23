## Context

见 [proposal.md](proposal.md)。当前 API 的 `async stream()` 直接迭代同步 `WorkflowEventAdapter.events()` / `graph.stream()`；各图节点通过同步 `BaseNode.__call__` 调用模型，`LLMClient` 使用同步 OpenAI transport 和 `time.sleep`。现有 SDK 客户端未关闭默认重试；`deadline_at` 仅在节点开始前及图更新之间检查。CLI 仍依赖同步图调用，LangExtract 及车型目录 RPC 也是同步路径。现有 SSE 规格要求节点进度与终态事件保持稳定。

## Goals / Non-Goals

**Goals:**

- 让单个 API worker 在一个工作流等待 I/O 或同步节点时继续处理其他请求，并保持现有节点级 SSE 事件、结果、历史恢复和错误格式。
- 对工作流入场、实际 LLM 请求和同步 LangExtract 工作设置有限容量，避免线程或等待请求无限增长。
- 让传输重试次数与总耗时由 InOrder 统一约束，且保留 CLI 的同步调用路径。

**Non-Goals:**

- 不增加 token 级 SSE、用户或租户级配额、跨进程全局限流，也不改订单、车型业务算法。
- 不把整条同步工作流长期放入一个线程；车型目录 RPC 暂保留已有短超时和缓存回退，由通用同步节点池承接。

## Decisions

### 1. API 只走异步图流，节点可逐个迁移

`WorkflowEventAdapter` 增加异步事件迭代，使用编译图的 `astream(stream_mode="updates", subgraphs=True, version="v2")`。适配器复用现有更新解析和结果组装逻辑，FastAPI 通过 `async for` 逐帧发送。生产 API 要求注入的图支持 `astream`；测试中的同步 fake graph 改为异步 fake，现有同步 `events()` 可留给同步调用方，不在 API 路径中回退到同步 `stream()`/`invoke()`。

图节点通过公开的双入口 runnable（同步 `func`、异步 `afunc`）接入同一张图。第一阶段异步入口把现有同步节点逐个提交到通用有界 executor，不依赖 LangGraph 1.x 某个版本对普通同步 callable 的内部 executor 策略。第二阶段，意图、重写、JSON 实体提取、货物画像等真正调用 LLM 的节点实现原生异步入口；同步入口继续供 CLI 使用。LangExtract 的同步提取走专用线程池。候选车型计算及短超时目录 RPC 暂走通用同步节点池。选择节点级承接，是为了保留实时 SSE 进度；整图放入单个线程再收集结果会推迟进度发送。

### 2. 入场与依赖容量分别受限

每个 API worker 在请求校验后、SSE 响应开始前申请工作流槽位。初始可配置默认值：`WORKFLOW_MAX_CONCURRENCY=8`、`WORKFLOW_MAX_WAITING=8`、`WORKFLOW_QUEUE_TIMEOUT_SECONDS=5`、`LLM_MAX_CONCURRENCY=8`、`LANGEXTRACT_MAX_THREADS=4`。通用同步节点池最多使用 `WORKFLOW_MAX_CONCURRENCY` 个线程。配置在服务启动时校验为正数；等待队列上限可设为 0，表示无等待。队列等待不得超过配置时限或本次 workflow deadline。满额或等待到期时，在响应头发出前返回 503 JSON，错误码为 `WORKFLOW_OVERLOADED`；429 留给未来的调用方配额限制。

原生异步 LLM 调用申请共享 LLM 槽位；LangExtract 调用同时受共享 LLM 槽位和专用线程槽位限制，内部并行度固定为 1，避免绕开上游并发预算。依赖槽位等待受队列时限和剩余 deadline 约束。流开始后若依赖等待时限先到，发送一个 `WORKFLOW_OVERLOADED` SSE `ERROR`；若工作流 deadline 先到，发送 `WORKFLOW_TIMEOUT`，均不再发送 `DONE`。工作流槽位由响应执行范围持有，在完成、失败、流尚未开始就断开、或取消时释放；同步任务的线程槽位由实际 worker future 完成时释放，不能仅因等待它的请求被取消就提前释放。通用同步节点池也遵守这一规则。

容量仅对当前 API worker 生效。部署多个 worker 时总容量约为各 worker 上限之和；若以后需要全局配额，应在网关或共享服务层实现，不在本变更中加入分布式协调。

### 3. 异步 LLM 复用现有语义与统一 deadline

为 OpenAI-compatible transport 增加 `AsyncOpenAI` 路径，覆盖 Chat Completions / Responses；`LLMClient` 增加返回完整 `LLMResponse` 的异步调用，按原配置支持异步消费模型 stream。格式修复 helper、模型 resolver、相关图节点增加异步入口。同步客户端和 CLI 保持既有返回类型。异步重试使用非阻塞等待，所有尝试沿用现有错误分类及“模型文本已交付后不重放流”的边界。

同步与异步 SDK 客户端均设置 `max_retries=0`，由 `LLMClient` 唯一计算传输尝试次数；格式修复仍是 resolver 层最多一次独立请求。`deadline_at` 从请求 state 显式传至模型、格式修复和 LLM 客户端。每次调用先检查剩余时间，并将上游单次 timeout 限制为 `min(LLM_TIMEOUT, 剩余时间)`；退避等待和有效 `Retry-After` 也不得越过 deadline。无法满足服务端要求的 `Retry-After` 时终止重试，不提早发送请求。同步 CLI 未提供 workflow deadline 时，仍使用原单次 timeout 和配置的有限重试。

LangExtract 使用独立的同步 provider，不能假定 `LLMClient` 的重试设置会约束它。适配器须显式配置其底层 SDK 的有限 timeout、零 SDK retry、单次提取内部并行度，并通过测试核对 pinned LangExtract 版本的行为；不做进程级 monkey patch。若同步调用无法即时取消，保留真实线程占用直到它在有限 transport timeout 后退出。

### 4. 取消是控制流程，不生成终态事件

异步适配器/API 只捕获需要转换为 `ERROR` 的业务异常，让请求取消直接向上抛出；不以 `BaseException` 吞掉取消。断开时停止消费 `astream`、停止调度后续节点，已启动的同步工作继续被容量管理器计数直到完成。工作流 deadline 由请求入场前开始计时；流内超时使用 `WORKFLOW_TIMEOUT`，入场等待耗尽则因尚未发送响应头而返回 503。使用与项目声明的 Python 版本兼容的异步超时原语。

## Risks / Trade-offs

- [LangGraph 版本差异可能改变异步节点分派或子图更新形态] → 用公开的双入口 runnable 接入节点；覆盖当前版本和依赖范围内的最低受支持版本，若不兼容则收紧依赖版本。
- [取消 SSE 后，同步网络调用仍可短暂运行] → 配置有限 transport timeout，保留线程槽位直到 future 实际完成，并验证断开后的容量统计。
- [LLM 与 LangExtract 内部上游调用难以完全共享一个计数] → 给 LangExtract 显式配置单线程内部执行，使用同一个 LLM 槽位包住提取调用，并以模拟并发测试确认实际上游请求上限。
- [过低的初始容量限制会增加 503] → 所有上限可配置；在部署前用目标并发下的响应时间、拒绝率和线程占用测试调整默认值。
- [同步 CLI 与异步 API 维护双入口] → 共用模型响应归一化、错误类型、重试策略和格式解析测试，防止两条路径结果漂移。

## Migration Plan

1. 先加入容量管理、节点级有界 executor、异步 `astream` 适配与并发/取消测试，使 API 事件循环不再执行同步节点。
2. 再加入异步 transport、客户端、格式修复和 LLM 节点入口；同时关闭同步/异步 SDK 默认重试并传播 deadline，单独校验 LangExtract provider。
3. 运行现有业务与 SSE 回归测试，并在目标并发下检查 p95 延迟、503 比例、事件循环响应、实际线程数和上游调用次数。若出现回归，回滚本次部署版本；不启用会重新阻塞事件循环的运行时回退路径。
