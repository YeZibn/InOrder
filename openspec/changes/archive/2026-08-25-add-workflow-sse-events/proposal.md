## Why

当前 InOrder 只有 CLI 级别的同步结果和 LLM 内容输出，调用方无法稳定感知 LangGraph 工作流正在执行哪个阶段，也无法在订单上下文更新时及时获得结构化结果。现在引入 HTTP 接口和 SSE 工作流事件，可以让前端或其他客户端以统一协议展示可解释的处理进度，并接收最终订单上下文。

## What Changes

- 新增 `POST /api/v2/chat` SSE 接口，接收会话、消息、历史对话和可选订单上下文。
- 为主图及订单子图增加稳定的工作流阶段事件：`THINKING_START`、`THINKING_STEP`、`THINKING_DONE`、`CREATE_ORDER_CONTEXT`、`DONE`。
- 为订单链路和问答链路定义不同但可预测的事件顺序，并在订单上下文更新后发送结构化快照。
- 统一 SSE 数据帧格式、事件载荷、错误事件和客户端断连处理。
- 保留现有 LangGraph 父图/子图边界，不改变 CLI 的同步调用协议。

## Capabilities

### New Capabilities

- `workflow-sse-events`: 通过 HTTP SSE 暴露 LangGraph 工作流阶段、订单上下文和终态事件。

### Modified Capabilities

- `main-parent-graph`: 为主图路由及子图阶段增加可观察的工作流事件发布要求，同时保持现有业务输出兼容。

## Impact

- 新增 API、SSE 事件模型与事件发布适配层。
- 改造主图、意图图和订单子图的节点包装或事件发布逻辑。
- 可能新增 FastAPI/Uvicorn 运行依赖及 API 测试依赖。
- 不改变现有 CLI 命令和 LLM 客户端对外行为；SSE 首版传递阶段事件，不将每个 LLM token 作为主要协议。
