## MODIFIED Requirements

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
