# delta

## MODIFIED Requirements

### Requirement: Return conversation recovery state

成功结束时 `DONE` 事件 SHALL 返回规范化的会话 `history` 或等价 `history_patch`；发生 `ERROR` 或客户端断开时不得伪造 assistant 内容，调用方可保留 pending user 回合并重试。历史快照中 assistant turn 的内容 SHALL 来自订单工作流的最终总结（`order_summary.user_message`），且服务端在消费结构化结果时 SHALL 对带 `to_dict()` 的领域对象先做字典化转换后再取字段。

#### Scenario: DONE includes recovered history

- **WHEN** 工作流成功完成
- **THEN** DONE payload 包含无重复消息的可持久化 history 或 history_patch

#### Scenario: Assistant turn carries order summary

- **WHEN** 订单子图执行完成且 `order_summary` 在结果中为 dataclass 对象（非 dict）
- **THEN** 历史 assistant turn 内容为该对象的 `user_message` 字段值，而非意图兜底文案

#### Scenario: No order summary falls back to intent

- **WHEN** 结果中不存在可提取的订单总结（如仅意图分类或 QA 分支）
- **THEN** assistant turn 使用意图摘要素材；完全无可提取内容时才使用简短兜底文案

#### Scenario: Error omits assistant summary

- **WHEN** 工作流发生错误或客户端断开
- **THEN** ERROR payload 不包含 assistant 摘要，客户端可继续使用原 pending history
