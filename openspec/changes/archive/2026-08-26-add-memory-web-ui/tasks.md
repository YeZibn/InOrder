## 1. Static UI and serving

- [x] 1.1 创建无需构建的单页 HTML/CSS/JavaScript 测试页面
- [x] 1.2 在 FastAPI 根路径提供同源页面，并保持 `/api/v2/chat` 行为兼容

## 2. SSE interaction

- [x] 2.1 使用 fetch POST 请求发送 `session_id`、`message`、`history`、`order_context` 和 `reference_time`
- [x] 2.2 实现 SSE 帧解析并展示 THINKING、CREATE_ORDER_CONTEXT、DONE 和 ERROR 事件
- [x] 2.3 处理空消息、请求中状态、网络错误和服务端错误

## 3. In-memory conversation state

- [x] 3.1 保存并展示当前消息、history、order_context 和 session_id
- [x] 3.2 收到上下文或终态结果时更新完整 order_context，并在下一轮请求中复用
- [x] 3.3 追加精简 assistant 摘要，避免把完整 SSE payload 写入 history
- [x] 3.4 实现清空会话并恢复初始状态

## 4. Verification and documentation

- [x] 4.1 增加页面路由和关键 SSE 状态处理测试
- [x] 4.2 更新 README 的 API/前端启动与使用说明
- [x] 4.3 运行完整测试集与 OpenSpec 严格校验

## 5. Friendly real-time progress hints

- [x] 5.1 增加 SSE 事件类型和公开阶段到用户友好提示的映射适配层
- [x] 5.2 实现事件到达后的实时当前状态展示，并保留简短的已完成提示记录
- [x] 5.3 处理 `CREATE_ORDER_CONTEXT`、`THINKING_DONE`、`DONE` 和 `ERROR` 的提示、加载状态及结果展示
- [x] 5.4 增加前端事件映射、未知阶段兜底和错误状态测试，确保不暴露技术事件名或原始 payload
- [x] 5.5 运行完整测试集与 OpenSpec 严格校验
