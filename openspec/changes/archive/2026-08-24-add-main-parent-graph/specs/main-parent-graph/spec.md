## Purpose

为 InOrder 提供一个真正的 LangGraph 父图，统一编排意图识别子图与订单处理子图，并在不同主意图之间进行可观测、可测试的状态路由。

## ADDED Requirements

### Requirement: Provide a main parent graph

系统 SHALL 提供一个 MainGraph 作为 full 链路入口，并以现有意图图和订单处理图作为可复用子图参与执行。

#### Scenario: Parent graph accepts full chain state
- **WHEN** 调用方提供消息、历史对话、订单上下文和参考时间
- **THEN** MainGraph 调用意图子图并保留这些上下文供后续订单子图使用

#### Scenario: Route order intent to order subgraph
- **WHEN** 意图子图输出 `main_intent=order`
- **THEN** MainGraph 调用订单处理子图并汇总订单解析结果

#### Scenario: Route qa intent to terminal branch
- **WHEN** 意图子图输出 `main_intent=qa`
- **THEN** MainGraph 不调用订单处理子图，并返回 QA 占位结果

### Requirement: Preserve child graph boundaries

父图 SHALL 通过明确的输入/输出状态挂载子图，不得复制子图内部节点逻辑或改变其节点执行顺序。

#### Scenario: Intent subgraph remains independently callable
- **WHEN** 调用方直接使用意图链路
- **THEN** 意图子图仍可独立执行并返回原有 `intent_plan`

#### Scenario: Order subgraph remains independently callable
- **WHEN** 调用方直接使用下单链路
- **THEN** 订单子图仍可独立执行并返回原有 rewrite、entities、OrderContext 和车型结果

### Requirement: Preserve parent result compatibility

MainGraph SHALL 将子图结果汇总为现有 full CLI 可消费的 `intent_result` 和 `order_result` 结构，并保留订单上下文更新状态。

#### Scenario: Order result compatibility
- **WHEN** order 子图完成
- **THEN** 父图结果包含 intent_result、order_result 及可继续保存的更新后 OrderContext

#### Scenario: Child graph failure
- **WHEN** 任一子图抛出结构化错误
- **THEN** MainGraph 向调用方暴露该错误，不返回部分成功的订单结果
