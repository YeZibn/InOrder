## MODIFIED Requirements

### Requirement: Provide an order processing subgraph

系统 SHALL 提供独立的订单处理子图，接收本轮用户消息、参考时间、`HistoryConversation` 和 `OrderContext`，并返回重写结果、实体列表、更新后的订单上下文及车型解析结果；车型估算结果可以包含最多三个候选车型。

#### Scenario: Subgraph returns vehicle candidates
- **WHEN** 订单解析完成且用户车型不可用或缺失
- **THEN** 子图返回确定性计算得到的 0 至 3 个车型候选及其来源和原因

### Requirement: Keep parsing-only boundary

订单处理子图 SHALL 只负责 rewrite、grounded 实体提取、订单上下文更新、货物画像和确定性车型解析/估算；不得调用历史订单服务、订单创建或确认工具，不得写入数据库。用户车型匹配成功时不得因货物画像而替换车型。

#### Scenario: Vehicle estimation has no LLM selection call
- **WHEN** 子图进入车型估算阶段
- **THEN** 车型结果由车型主数据和确定性装载计算生成，不调用车型选择 LLM
