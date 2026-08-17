## MODIFIED Requirements

### Requirement: Provide an order processing subgraph

系统 SHALL 提供独立的订单处理子图，接收本轮用户消息、参考时间、`HistoryConversation` 和 `OrderContext`，并返回重写结果、实体列表、澄清状态及更新后的订单上下文。

#### Scenario: Subgraph accepts order parsing state

- **WHEN** 调用方提供有效的用户消息、参考时间、历史对话和订单上下文
- **THEN** 子图能够完成订单语义解析并返回结构化结果

#### Scenario: Subgraph returns updated context

- **WHEN** 子图提取出可应用到订单草稿的实体
- **THEN** 子图返回基于输入订单上下文和本轮实体计算出的新 `OrderContext`

#### Scenario: Subgraph does not mutate input context

- **WHEN** 子图完成一次解析并返回更新后的订单上下文
- **THEN** 输入的历史对话和原始 `OrderContext` 保持不变

### Requirement: Keep parsing-only boundary

订单处理子图 SHALL 只负责 rewrite、澄清路由、实体提取和内存订单上下文更新；不得调用历史订单服务、订单创建或确认工具，不得写入数据库。

#### Scenario: Parsing applies entities in memory only

- **WHEN** 子图提取出带 action 的订单实体
- **THEN** 子图将实体应用到当前 `OrderContext` 并返回新上下文，不触发外部业务副作用

#### Scenario: Clarification does not update context

- **WHEN** rewrite 触发澄清并跳过 extract
- **THEN** 子图返回原始订单上下文作为当前上下文，不应用实体更新

#### Scenario: Structured failures do not update context

- **WHEN** rewrite 或 extract 因结构化输出错误导致子图失败
- **THEN** 子图不返回部分更新后的上下文

