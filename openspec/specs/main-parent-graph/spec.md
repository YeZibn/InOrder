# main-parent-graph Specification

## Purpose

为 InOrder 提供一个真正的 LangGraph 父图，统一编排意图识别子图与订单处理子图，并在不同主意图之间进行可观测、可测试的状态路由。
## Requirements
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
- **THEN** 意图子图仍可独立执行并返回主意图分类结果，不调用子意图识别

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

MainGraph SHALL 为 full 工作流提供稳定的公开生命周期：开始、识别用户意图、订单子图中实际完成的节点进度、可选货物画像、可选车型处理、完成或错误。事件内容 SHALL 由父图路由和子图状态更新派生，不得复制子图节点实现，也不得暴露 prompt、原始 LLM 输出或内部思维。

#### Scenario: Order route publishes business lifecycle

- **WHEN** MainGraph 路由到订单子图并执行其节点
- **THEN** 事件观察者可按实际顺序看到 `THINKING_START`、意图及订单子图节点完成对应的公开 `THINKING_STEP`、可选 `CREATE_ORDER_CONTEXT`、`THINKING_DONE` 和 `DONE`

#### Scenario: Internal order nodes are not public stages

- **WHEN** 订单子图执行 rewrite、extract 或 update_context
- **THEN** 事件观察者可以收到安全的节点完成进度，但不能看到 prompt、原始模型输出或隐藏思维

#### Scenario: Parent observes nested updates without changing execution

- **WHEN** 父图通过流式观察子图更新
- **THEN** 父图只转发节点完成状态并汇总既有结果，不复制、重排或改变子图内部节点执行顺序

#### Scenario: QA route publishes lifecycle

- **WHEN** 主意图为 `qa` 并进入终止分支
- **THEN** 系统只发送开始、意图识别、完成和终态事件，不发送订单子图节点或订单上下文事件
