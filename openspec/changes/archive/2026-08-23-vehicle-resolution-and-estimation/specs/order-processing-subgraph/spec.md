## MODIFIED Requirements

### Requirement: Provide an order processing subgraph

系统 SHALL 提供独立的订单处理子图，接收本轮用户消息、参考时间、`HistoryConversation` 和 `OrderContext`，并返回重写结果、实体列表、更新后的订单上下文及车型解析结果。

#### Scenario: Subgraph returns vehicle resolution
- **WHEN** 订单解析完成且货物画像或用户车型信息可用于车型决策
- **THEN** 子图返回最终车型、特殊规格、来源和原因

### Requirement: Keep parsing-only boundary

订单处理子图 SHALL 只负责 rewrite、grounded 实体提取、订单上下文更新、货物画像和车型解析/估算；不得调用历史订单服务、订单创建或确认工具，不得写入数据库。用户车型匹配成功时不得因货物画像而替换车型。

#### Scenario: Vehicle resolution has no external side effect
- **WHEN** 子图执行车型解析或估算
- **THEN** 结果只更新内存中的订单状态和派生决策，不触发外部业务副作用

### Requirement: Preserve structured failure behavior

车型解析或估算的结构化输出失败时，子图 SHALL 暴露调用错误，并不得返回部分车型决策作为成功结果。

#### Scenario: Invalid vehicle estimation output
- **WHEN** 车型估算模型返回非法结构或未知车型 code
- **THEN** 子图调用失败，不写入非法车型结果
