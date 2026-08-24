## MODIFIED Requirements

### Requirement: Provide an order processing subgraph

系统 SHALL 提供可独立调用且可作为 MainGraph 子图挂载的订单处理子图，接收消息、参考时间、历史对话和订单上下文，并返回 rewrite、实体列表、更新后的订单上下文及车型解析结果。

#### Scenario: Parent graph passes order context
- **WHEN** MainGraph 路由到订单子图
- **THEN** 订单子图接收父图传入的历史对话、订单上下文和参考时间

#### Scenario: Order subgraph output returns to parent
- **WHEN** 订单子图完成解析
- **THEN** 父图可以取得 rewrite、entities、OrderContext 和车型结果并汇总返回
