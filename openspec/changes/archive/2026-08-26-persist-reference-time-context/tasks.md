## 1. OrderContext 数据契约

- [x] 1.1 为 `OrderContext` 增加可选 `reference_time` 字段，并确保默认空值和 JSON 序列化兼容旧上下文
- [x] 1.2 更新 HTTP 请求上下文解析，使传入的 `reference_time` 能够被读取、校验并保留
- [x] 1.3 更新上下文相关文档和类型/模型测试，覆盖空上下文、旧上下文和已保存时间

## 2. 请求入口时间解析

- [x] 2.1 实现统一的上下文时间优先级：`OrderContext.reference_time` > 请求级 `reference_time` > 当前 Asia/Shanghai 时间
- [x] 2.2 修改 CLI，使每轮消息开始前从当前 session 上下文解析时间，并将解析结果写回上下文
- [x] 2.3 修改 HTTP/SSE 入口，在构造 LangGraph state 前解析时间并同步写入上下文副本
- [x] 2.4 确保 `/clear` 和新建空上下文会清除时间锚点

## 3. 工作流传播与兼容

- [x] 3.1 将会话级 `reference_time` 继续传递到 MainGraph、OrderProcessingGraph、Rewrite 和 Extract
- [x] 3.2 确保货物画像、车型处理和结构化输出修复重试复用同一时间，不重新读取系统时钟
- [x] 3.3 保持 Python 请求无状态，不按 `session_id` 增加本地跨请求存储或覆盖上下文时间

## 4. 测试与验证

- [x] 4.1 增加首轮无时间时自动生成并写入上下文的测试
- [x] 4.2 增加后续轮次复用上下文时间、请求级时间冲突时上下文优先的 CLI/API 测试
- [x] 4.3 增加 Rewrite、Extract 及重试路径时间稳定性的测试
- [x] 4.4 运行完整测试集和 `openspec validate --strict`，确认旧请求格式保持兼容
