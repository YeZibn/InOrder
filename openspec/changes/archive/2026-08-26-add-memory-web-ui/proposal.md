## Why

当前 InOrder 主要通过 CLI 或手工 curl 调试，连续验证 SSE 阶段、多轮 `history` 和 `order_context` 传递成本较高。需要一个无需构建工具的轻量测试页面，直接在浏览器中体验完整订单解析链路。

## What Changes

- 新增同源内置 Web 测试页面，并由 Python API 根路径提供。
- 页面支持输入消息、发送 `POST /api/v2/chat` 并实时消费 SSE 事件。
- 浏览器内存保存当前 `session_id`、`history`、`order_context` 和消息列表，支持连续多轮请求。
- 展示意图识别、订单处理、货物画像、车型处理等公开阶段，以及最终结构化结果。
- 将 SSE 技术事件转换为面向用户的实时处理小提示，在事件到达后立即反馈进度，不直接展示事件名、内部节点名或原始 payload。
- 支持查看当前订单上下文与历史对话，并提供清空内存会话能力。
- 不引入前端构建链、数据库、浏览器持久化或断点续传能力。

## Capabilities

### New Capabilities

- `memory-web-ui`: 面向本地调试的内存型 SSE 订单测试页面。

### Modified Capabilities

- `workflow-sse-events`: 提供同源测试页面入口，并保持现有 `/api/v2/chat` 契约不变。

## Impact

新增静态 HTML/CSS/JavaScript 资源和 FastAPI 静态页面路由；不改变现有 SSE 事件结构和请求字段。运行 `inorder-api` 后可通过浏览器访问 `http://localhost:8000/`。
