## Context

当前 full 链路由 LangGraph MainGraph 同步执行，CLI 通过最终状态渲染结果；意图图和订单处理图已具备独立边界，订单图包含 rewrite、extract、上下文更新以及可选货物画像和车型节点。项目目前没有面向外部客户端的 HTTP/SSE 层。详见 `proposal.md` 和本 change 的 delta specs。

## Goals / Non-Goals

**Goals:**

- 增加一个面向客户端的 `POST /api/v2/chat` SSE 入口。
- 将父图路由和订单子图公开节点映射为稳定的生命周期事件。
- 提供可持久化的 `OrderContext` 快照和归一化错误事件。
- 保持现有 CLI、意图子图、订单子图和同步 MainGraph 结果兼容。

**Non-Goals:**

- 不把每个 LLM token 作为工作流 SSE 的主要协议。
- 不公开 prompt、原始模型响应、供应商调试字段或内部思维内容。
- 不在本 change 中实现订单业务执行、历史订单存储或新的归一化规则。

## Decisions

### 1. Use a workflow event adapter around MainGraph

事件层采用独立适配器消费 MainGraph 的公开阶段和最终状态，而不是复制或重写父图、意图图、订单图的节点逻辑。这样可以保持父子图边界，并让同步 `invoke` 与 SSE 入口共享同一条业务链路。

替代方案是为每个节点分别实现一套 HTTP 流程；该方案会产生两套路由逻辑，容易造成 CLI 与 API 行为漂移，因此不采用。

### 2. Use typed event envelopes

所有 SSE 帧使用统一的 `{type, payload}` JSON envelope。事件类型采用大写稳定值：`THINKING_START`、`THINKING_STEP`、`THINKING_DONE`、`CREATE_ORDER_CONTEXT`、`DONE` 和 `ERROR`。阶段 payload 只包含公开标题、摘要、序号和必要的 intent；上下文事件携带结构化快照。

替代方案是使用供应商原始 SSE 事件或将文本直接作为 data；这会把传输协议绑定到 LLM 提供方，且客户端难以区分工作流阶段，因此不采用。

### 3. Emit workflow stages, not hidden reasoning

阶段事件由已知 LangGraph 节点和路由产生，内容使用固定的安全文案。LLM 增量文本仍由现有 LLM streaming 能力负责，不作为本协议的阶段事件来源，也不将模型的隐藏推理发送给客户端。

### 4. Keep errors terminal and normalized

事件适配器捕获子图和上游 LLM 异常，映射为包含稳定错误码、阶段和安全消息的单个 `ERROR` 事件；错误后关闭流并不发送 `DONE`。同步入口继续保留原有异常传播语义。

### 5. Treat disconnect as cancellation

SSE 生成器在检测到客户端断开后停止消费和发布后续事件，并释放请求级资源。若底层执行无法立即取消，至少不得继续写入已关闭连接，并记录取消状态。

## Risks / Trade-offs

- [Risk] LangGraph 当前同步 `invoke` 难以在节点执行中自然产出事件 → Mitigation: 首版在父图/子图边界和状态更新处发布阶段事件；若后续需要 token 级流式，再单独扩展异步 stream adapter。
- [Risk] 阶段文案和节点名称变化会影响客户端展示 → Mitigation: 事件类型保持稳定，阶段标题作为可本地化展示字段，不让客户端依赖内部节点名。
- [Risk] 订单上下文包含敏感联系信息 → Mitigation: SSE 只发送现有可持久化结构化快照，并在 API 层明确鉴权和日志脱敏边界。
- [Risk] 客户端断连时后台工作可能继续占用资源 → Mitigation: 生成器使用断连检查和取消信号，后续再补充执行超时与后台任务治理。

## Migration Plan

1. 增加事件模型、事件适配器和 HTTP SSE 路由，复用现有 MainGraph 构造逻辑。
2. 为订单和 QA 两条路由添加事件顺序、上下文快照、错误和断连测试。
3. 在本地以 Uvicorn 启动 API；现有 `inorder` CLI 继续使用同步入口。
4. 若需要回滚，移除或关闭 `/api/v2/chat` 路由即可，不迁移已有 CLI 或持久化数据。

## Open Questions

- 生产环境的鉴权、限流和跨域策略可在 API 部署阶段确定，不改变本 change 的事件协议。
