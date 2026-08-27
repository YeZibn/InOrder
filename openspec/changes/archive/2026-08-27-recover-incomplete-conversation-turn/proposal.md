## Why

网络中断、客户端超时或进程异常可能使当前会话只持久化了最后一条 user 消息，而没有 assistant 回复。下一轮请求若直接追加新消息，会造成连续 user 回合、上下文重复和订单语义丢失，因此需要在工作流入口统一恢复未完成回合。

## What Changes

- 在 API/CLI 入口增加未完成会话回合检测：最后一条为 user 且其后没有 assistant 时，将其视为 pending turn。
- 将 pending turn 与当前新 message 合并后再进入意图识别和订单解析；支持“重试/继续”等控制词只重放 pending turn，避免重复追加。
- 对连续多个未完成 user 回合按一个待恢复消息块处理，并避免相同消息重复拼接。
- 在成功结果中返回规范化的 history 或 history patch，使调用方可以持久化恢复后的完整 user/assistant 回合。
- 保持现有 HistoryConversation、OrderContext 和业务图职责不变；暂不引入外部数据库或真正下单幂等。

## Capabilities

### New Capabilities
- `conversation-turn-recovery`: 检测、合并和确认未完成会话回合。

### Modified Capabilities
- `conversation-order-context`: 明确会话历史回合完整性与恢复后的持久化快照。
- `workflow-sse-events`: DONE 结果携带历史修复信息，支持断线后的客户端恢复。
- `cli-chain-entrypoints`: CLI 在执行新消息前修复悬空 user 回合并更新本地历史。

## Impact

影响 `workflow/api.py`、CLI 会话处理、SSE DONE payload、HistoryConversation 序列化及相关测试和文档。当前订单解析图、Rewrite、Extract 和 OrderContext 字段不变；不增加外部依赖。
