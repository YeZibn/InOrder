## MODIFIED Requirements

### Requirement: Provide an order processing subgraph

系统 SHALL 提供独立、可测试且仅负责语义解析的订单处理子图，接收本轮用户消息、参考时间、`HistoryConversation` 和 `OrderContext`，依次执行 Rewrite、Extract、上下文合并、货物画像（若启用）、车型处理（若启用）和订单完整性检查，返回重写结果、实体列表、更新后的订单上下文、车型解析及候选等级、结构化订单摘要以及面向用户的自然语言回复。车型解析结果可以包含 0 至 3 个标记为 `lower_bound_fit` 或 `upper_bound_only` 的候选车型；只有 `lower_bound_fit` 估算主候选可以写入订单上下文，`upper_bound_only` 候选不得作为已选车型写入。用户明确指定的车型 SHALL 保持不变。该子图不得执行真实下单或外部订单副作用。

#### Scenario: Subgraph accepts order parsing state
- **WHEN** 调用方提供有效的用户消息、参考时间、历史对话和订单上下文
- **THEN** 子图能够完成订单语义解析并返回结构化结果

#### Scenario: Subgraph returns updated context
- **WHEN** 子图提取出可应用到订单草稿的实体
- **THEN** 子图返回基于输入订单上下文和本轮实体计算出的新 `OrderContext`

#### Scenario: Subgraph returns vehicle resolution
- **WHEN** 订单解析完成且货物画像或用户车型信息可用于车型决策
- **THEN** 子图返回最终车型、特殊规格、来源和原因

#### Scenario: Subgraph returns ranked vehicle candidates
- **WHEN** 订单解析完成且用户车型不可用或缺失
- **THEN** 子图返回确定性计算得到的 0 至 3 个候选、各自的适配等级和排序原因

#### Scenario: Keep lower-bound candidates ahead of upper-bound-only candidates
- **WHEN** 下界通过和仅上界通过的候选同时存在
- **THEN** 子图返回的候选列表 SHALL 将所有 `lower_bound_fit` 排在 `upper_bound_only` 之前

#### Scenario: Do not commit an upper-bound-only candidate
- **WHEN** 估算结果只有 `upper_bound_only` 候选，没有 `lower_bound_fit` 主候选
- **THEN** 子图返回这些候选，但不得将其中任何车型写入 `OrderContext.vehicle_type` 作为已选估算车型

#### Scenario: Keep an explicitly selected vehicle
- **WHEN** 用户明确指定的车型已匹配
- **THEN** 子图保留用户车型，不因其他估算候选而自动替换

#### Scenario: Process an order through the final summary node
- **WHEN** 订单上下文完成车型处理
- **THEN** 子图执行订单完整性检查作为最后一个节点，并在结果中返回订单状态、事实摘要和缺失字段提示

#### Scenario: Return an incomplete order without failure
- **WHEN** 订单缺少送达时间或其他最小字段
- **THEN** 子图正常完成并返回 `incomplete` 摘要，不将业务字段缺失当作 LangGraph 或 LLM 异常

#### Scenario: Subgraph does not mutate input context
- **WHEN** 子图完成一次解析并返回更新后的订单上下文
- **THEN** 输入的历史对话和原始 `OrderContext` 保持不变
