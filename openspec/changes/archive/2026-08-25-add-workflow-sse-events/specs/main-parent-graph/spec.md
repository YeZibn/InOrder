## MODIFIED Requirements

### Requirement: Provide a main parent graph

系统 SHALL 提供一个 MainGraph 作为 full 链路入口，并以现有意图图和订单处理图作为可复用子图参与执行。MainGraph SHALL 在执行过程中发布面向调用方的工作流阶段事件，但不得改变既有路由结果和同步结果结构。

#### Scenario: Parent graph accepts full chain state
- **WHEN** 调用方提供消息、历史对话、订单上下文和参考时间
- **THEN** MainGraph 调用意图子图并保留这些上下文供后续订单子图使用，同时允许事件发布层读取当前公开阶段

#### Scenario: Route order intent to order subgraph
- **WHEN** 意图子图输出 `main_intent=order`
- **THEN** MainGraph 调用订单处理子图并汇总订单解析结果，同时发布订单链路对应的阶段事件

#### Scenario: Route qa intent to terminal branch
- **WHEN** 意图子图输出 `main_intent=qa`
- **THEN** MainGraph 不调用订单处理子图，并返回 QA 占位结果，同时发布问答链路的终止阶段事件

### Requirement: Preserve child graph boundaries

父图 SHALL 通过明确的输入/输出状态挂载子图，不得复制子图内部节点逻辑或改变其节点执行顺序。事件发布 SHALL 通过节点边界、状态更新或独立适配层观察子图阶段，不得将子图节点实现复制到父图。

#### Scenario: Intent subgraph remains independently callable
- **WHEN** 调用方直接使用意图链路
- **THEN** 意图子图仍可独立执行并返回原有 `intent_plan`，不强制要求 SSE 调用方

#### Scenario: Order subgraph remains independently callable
- **WHEN** 调用方直接使用下单链路
- **THEN** 订单子图仍可独立执行并返回原有 rewrite、entities、OrderContext 和车型结果，不强制要求 SSE 调用方

### Requirement: Preserve parent result compatibility

MainGraph SHALL 将子图结果汇总为现有 full CLI 可消费的 `intent_result` 和 `order_result` 结构，并保留订单上下文更新状态。增加事件发布能力不得删除或重命名现有同步结果字段。

#### Scenario: Order result compatibility
- **WHEN** order 子图完成
- **THEN** 父图结果包含 intent_result、order_result 及可继续保存的更新后 OrderContext，并可由 SSE 适配层作为最终业务结果使用

#### Scenario: Child graph failure
- **WHEN** 任一子图抛出结构化错误
- **THEN** MainGraph 向同步调用方暴露该错误，不返回部分成功的订单结果；SSE 适配层将其转换为 `ERROR` 事件

### Requirement: Publish parent workflow lifecycle

MainGraph SHALL 为 full 工作流提供稳定的公开生命周期：开始、阶段进度、完成或错误。事件内容 SHALL 由父图当前路由和子图公开状态派生，不得包含 prompt、原始 LLM 输出或内部思维内容。

#### Scenario: Order route publishes lifecycle
- **WHEN** MainGraph 路由到订单子图并完成订单处理
- **THEN** 事件观察者可按顺序看到 `THINKING_START`、公开阶段 `THINKING_STEP`、可选 `CREATE_ORDER_CONTEXT`、`THINKING_DONE` 和 `DONE`

#### Scenario: QA route publishes lifecycle
- **WHEN** MainGraph 路由到 QA 终止分支
- **THEN** 事件观察者可看到 `THINKING_START`、意图识别阶段、`THINKING_DONE` 和 `DONE`，且不会看到订单上下文事件
