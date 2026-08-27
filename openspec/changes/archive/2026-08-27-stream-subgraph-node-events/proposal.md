## Why

当前 SSE 只观察父图边界，订单子图被当作一个整体节点；Rewrite、Extract、上下文更新和画像/车型处理期间前端长时间没有新事件，用户难以判断工作流是否仍在运行。LangGraph 已支持透传嵌套子图更新，因此应将节点完成状态安全地转换为逐节点进度事件。

## What Changes

- 开启父图对子图更新的观察，捕获意图子图和订单子图每个节点完成事件。
- 为子图节点建立稳定的公开阶段/提示映射，并按完成顺序发送 `THINKING_STEP`，不暴露 prompt、原始模型响应或内部堆栈。
- 扩展 SSE 进度事件 payload，使客户端能够区分阶段、节点完成状态和序号，同时保持现有终态事件兼容。
- 调整 Web 测试页面，按事件到达顺序逐条展示节点级友好进度，避免相同阶段提示被折叠。
- 增加嵌套子图流式事件、事件顺序、QA 分支、错误和前端映射的测试覆盖。

## Capabilities

### New Capabilities

- `subgraph-node-sse-progress`: 提供父图及嵌套子图节点完成级别的安全 SSE 进度事件。

### Modified Capabilities

- `workflow-sse-events`: 将公开进度从聚合业务阶段扩展为可选的子图节点完成事件，并保持生命周期、错误和终态协议。
- `main-parent-graph`: 父图事件观察需要透传嵌套子图节点边界，但不复制子图实现。
- `memory-web-ui`: 前端按节点完成事件实时追加用户友好提示。

## Impact

- 影响 `workflow` SSE 适配层、事件模型和 `/api/v2/chat` 的流式输出行为。
- 影响 `frontend/index.html` 的进度渲染和相关测试。
- 依赖当前 LangGraph 版本的 `subgraphs=True`、`stream_mode="updates"`（优先使用 v2 事件格式）。
- 不改变业务节点执行顺序、同步图结果、LLM token 是否展示及已有 `DONE`/`ERROR` 语义。
