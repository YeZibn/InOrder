## 1. Recovery model

- [x] 1.1 新增 pending turn 检测与连续 user 消息合并纯函数
- [x] 1.2 定义重试控制词、相同消息去重和恢复结果数据结构

## 2. API and workflow integration

- [x] 2.1 在 API 请求入口应用 history 恢复并将合并 message 传入工作流
- [x] 2.2 在 DONE payload 返回规范化 history 或 history_patch
- [x] 2.3 确保 ERROR/断开路径不追加伪造 assistant 内容

## 3. CLI and frontend integration

- [x] 3.1 在 CLI 执行前恢复 pending turn，成功后更新本地 HistoryConversation
- [x] 3.2 前端消费 DONE 中的 history/history_patch，失败时保留 pending user 状态

## 4. Tests and documentation

- [x] 4.1 增加完整 history、pending user、连续 user 和控制词重试测试
- [x] 4.2 增加 API/CLI 断线恢复及避免重复拼接回归测试
- [x] 4.3 更新 SSE、会话历史规格、README 和变更记录
- [x] 4.4 运行全量测试与 OpenSpec 严格校验
