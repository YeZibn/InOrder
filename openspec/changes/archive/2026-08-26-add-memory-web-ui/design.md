## Context

当前 API 已提供 `POST /api/v2/chat` SSE 接口，但没有浏览器入口。测试需求以本地调试为主，要求低依赖、可连续验证多轮上下文，且不改变现有后端工作流协议。

## Goals / Non-Goals

**Goals:**

- 通过 FastAPI 同源提供一个单页测试界面。
- 使用原生浏览器 API 消费 POST SSE 流。
- 在页面内存中维护会话快照并支持多轮订单解析。
- 清晰展示公开阶段、错误、最终结果和上下文。

**Non-Goals:**

- 不引入 React/Vue、npm、打包器或额外运行时。
- 不使用 localStorage、数据库或服务端 session 存储。
- 不实现 SSE 断线续传、checkpoint 或生产级权限控制。

## Decisions

### 1. 使用原生静态资源

使用单个 HTML 文件内嵌 CSS/JavaScript，减少启动和部署复杂度。相比独立前端开发服务器，同源页面不需要 CORS 或代理配置。

### 2. 使用 fetch + ReadableStream

原生 `EventSource` 只支持 GET，当前接口是 POST，因此页面使用 `fetch` 发送 JSON，并通过 `ReadableStream` 按空行解析 SSE `data:` 帧。

### 3. 以内存对象作为唯一会话状态

页面维护 `session_id`、`history`、`order_context`、消息和当前请求状态。收到 `CREATE_ORDER_CONTEXT` 立即更新上下文，收到 `DONE` 再从最终结果兜底更新；刷新页面即重置。

### 4. 只写入精简 assistant 摘要

为避免污染下一轮 Rewrite，history 只追加阶段完成和上下文更新等简短摘要，不保存完整 SSE payload。

### 5. 通过适配层呈现友好进度

页面增加“技术事件 → 用户提示”的适配层。适配层按公开事件类型和 `stage` 生成稳定的中文短句，例如将 `THINKING_START` 转为“正在理解您的需求…”，将 intent、order、cargo_profile、vehicle 等阶段分别转为识别运输需求、整理订单信息、分析货物特征和匹配车型的提示。未知阶段使用通用的“正在处理您的订单…”提示，不把原始事件名泄露给用户。

页面同时维护三个相互独立的展示状态：当前处理中提示、已完成提示列表和最终结果。阶段事件到达即更新当前提示，并可将前一阶段保留为简短完成记录；`CREATE_ORDER_CONTEXT` 追加“订单信息已更新”；`THINKING_DONE`/`DONE` 结束处理中状态，`ERROR` 则以错误样式结束并阻止成功提示。

## Risks / Trade-offs

- [刷新后数据丢失] → 明确定位为临时测试工具，提供手动查看和清空按钮。
- [SSE 解析异常] → 按标准 `\n\n` 帧边界处理，并忽略非 `data:` 行。
- [后端未启动或请求失败] → 在页面显示网络错误并恢复发送按钮。
- [长 JSON 影响可读性] → 使用折叠/滚动代码区域展示上下文和结果。
