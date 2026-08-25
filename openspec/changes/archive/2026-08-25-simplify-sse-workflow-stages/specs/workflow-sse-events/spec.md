## MODIFIED Requirements

### Requirement: Emit order workflow lifecycle events

订单主意图进入订单子图时，系统 SHALL 对外只发送用户可理解的业务阶段：识别用户意图、处理订单、生成货物画像（若执行）和处理车型（若执行）。rewrite、extract、上下文合并等内部步骤 SHALL 归属于“处理订单”阶段，不得作为独立的公开 `THINKING_STEP`。

#### Scenario: Stream an order workflow with optional stages
- **WHEN** 主意图识别结果为 `order`
- **THEN** 事件依次覆盖识别用户意图、处理订单，以及实际执行的货物画像和车型处理阶段，随后发送思考完成和终态事件

#### Scenario: Hide order implementation details
- **WHEN** 订单子图执行 rewrite、extract 或 update_context 节点
- **THEN** SSE 流不得发送这些内部节点名称或独立阶段事件

#### Scenario: Stream a minimal order workflow
- **WHEN** 订单子图未启用货物画像或车型处理节点
- **THEN** SSE 只发送识别用户意图和处理订单阶段，不发送虚假的可选阶段
