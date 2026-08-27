## Context

当前 `WorkflowEventAdapter` 以父图 `stream_mode="updates"` 观察执行，嵌套子图默认被折叠为单个父节点更新。LangGraph 的嵌套流可以返回带 namespace 的子图更新；API 需要继续保持同步业务结果和现有 SSE 终态协议。

## Goals / Non-Goals

**Goals:**

- 在单次请求内按子图节点完成顺序产生安全、可预测的 `THINKING_STEP`。
- 同时兼容 LangGraph v1 元组格式和 v2 `{type, ns, data}` 格式（如运行环境需要）。
- 对意图、订单及可选画像/车型节点提供稳定的公开阶段和友好标题。
- 让前端逐条追加进度，保留现有上下文、摘要、history 和终态展示。

**Non-Goals:**

- 不展示 LLM token、原始 JSON、prompt 或隐藏思维。
- 不改变图的业务路由、节点顺序、重试策略或同步返回结构。
- 不引入服务端持久化、跨请求任务恢复或新的模型依赖。

## Decisions

1. **使用嵌套子图 updates 观察。** 适配器调用父图 `stream(..., stream_mode="updates", subgraphs=True)`；优先解析 v2 事件，必要时回退 v1 元组。这样可以获得真实节点边界，无需复制子图逻辑。只将带 namespace 的子图更新转换为进度，父图聚合更新仅用于累积最终结果。

2. **事件按节点完成发送。** 每个子图更新中的节点只发送一次 `THINKING_STEP`，payload 包含 `stage`、稳定 `node`、`status="completed"`、递增 `sequence` 和安全 `title`。父图节点使用既有聚合阶段映射，避免重复公开同一子图节点。

3. **稳定映射而非透传文本。** 维护内部节点到公开阶段/标题的白名单；未知节点不发送或归入安全的通用订单阶段，不透传节点返回值。这样可兼容未来新增节点并避免泄露业务状态。

4. **前端追加而非按文案去重。** 前端以事件序号/节点完成事件为记录单位，允许同一阶段出现多条不同提示；仍由现有 `friendlyHint` 控制用户可见文案。

5. **保持终态事件顺序。** 所有节点事件位于 `THINKING_START` 与 `THINKING_DONE` 之间；`CREATE_ORDER_CONTEXT` 仍只在最终上下文确实更新时发送，`DONE`/`ERROR` 逻辑不变。

## Risks / Trade-offs

- [LangGraph 版本差异] → 编写 v1/v2 解析器和 fake graph 测试；若不支持 `subgraphs`，保留聚合更新兼容路径。
- [同一节点可能在重试或父图聚合中重复出现] → 以 namespace、节点名和本次运行集合去重，仅在首次完成时发事件。
- [节点标题过多导致界面噪声] → 只公开订单关键节点白名单，并在前端使用紧凑的完成记录。
- [同步生成器阻塞心跳] → 本 change 只解决节点完成级刷新；token 级推送和长节点心跳另行设计。

## Migration Plan

先升级事件适配器和前端，旧客户端忽略新增 `THINKING_STEP` payload 字段即可继续工作。若发现下游不兼容，可关闭 `subgraphs` 观察并回退到现有聚合阶段映射，不影响业务结果和终态事件。
