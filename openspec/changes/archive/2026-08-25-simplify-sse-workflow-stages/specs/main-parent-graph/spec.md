## MODIFIED Requirements

### Requirement: Publish parent workflow lifecycle

MainGraph SHALL 为 full 工作流提供稳定的公开生命周期：开始、识别用户意图、处理订单、可选货物画像、可选车型处理、完成或错误。事件内容 SHALL 由父图路由和子图公开结果派生，不得暴露内部节点名称、prompt、原始 LLM 输出或内部思维内容。

#### Scenario: Order route publishes business lifecycle
- **WHEN** MainGraph 路由到订单子图并完成订单处理
- **THEN** 事件观察者可按顺序看到 `THINKING_START`、识别用户意图、处理订单、可选画像/车型阶段、可选 `CREATE_ORDER_CONTEXT`、`THINKING_DONE` 和 `DONE`

#### Scenario: Internal order nodes are not public stages
- **WHEN** 订单子图执行 rewrite、extract 或 update_context
- **THEN** 事件观察者只能看到聚合后的处理订单阶段，不能依赖这些内部节点名称

#### Scenario: QA route publishes short lifecycle
- **WHEN** MainGraph 路由到 QA 终止分支
- **THEN** 事件观察者可看到 `THINKING_START`、识别用户意图、`THINKING_DONE` 和 `DONE`，且不会看到订单、画像、车型或订单上下文事件
