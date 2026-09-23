## MODIFIED Requirements

### Requirement: Preserve parent result compatibility

MainGraph SHALL 将意图子图和订单子图结果汇总为现有 full CLI 可消费的 `intent_result` 和 `order_result` 结构，并保留订单上下文更新状态。`intent_result` 至少包含 `main_intent`，可选包含 `confidence`，不得依赖或输出 `sub_intents`、步骤依赖等已删除字段。

#### Scenario: Order result compatibility
- **WHEN** order 子图完成
- **THEN** 父图结果包含 `intent_result`、`order_result` 及可继续保存的更新后 OrderContext，并可由 SSE 适配层作为最终业务结果使用

#### Scenario: Main-only intent result
- **WHEN** 意图子图完成
- **THEN** `intent_result` 包含 `main_intent` 和可选置信度，不包含 `sub_intents`

#### Scenario: Child graph failure
- **WHEN** 任一子图抛出结构化错误
- **THEN** MainGraph 向同步调用方暴露该错误，不返回部分成功的订单结果；SSE 适配层将其转换为 `ERROR` 事件

### Requirement: Preserve child graph boundaries

父图 SHALL 通过明确的输入/输出状态挂载子图，不得复制子图内部节点逻辑或改变其节点执行顺序。意图子图只输出主意图分类，订单子图继续负责 Rewrite、Extract、上下文更新和后续订单处理。

#### Scenario: Intent subgraph remains independently callable
- **WHEN** 调用方直接使用意图链路
- **THEN** 意图子图独立返回主意图分类结果，不调用子意图识别

#### Scenario: Order subgraph remains independently callable
- **WHEN** 调用方直接使用下单链路
- **THEN** 订单子图仍可独立执行并返回原有 rewrite、entities、OrderContext 和车型结果
