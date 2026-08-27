## MODIFIED Requirements

### Requirement: Emit order workflow lifecycle events

订单主意图进入订单子图时，系统 SHALL 对外发送识别用户意图、处理订单、生成货物画像（若执行）和处理车型（若执行）等公开业务阶段，并可在这些阶段内按子图节点完成发送更细粒度的 `THINKING_STEP`。节点事件必须按实际完成顺序出现；不得暴露 prompt、原始模型响应或内部思维。既有 `THINKING_START`、`THINKING_DONE`、`DONE` 和上下文事件语义保持不变。

#### Scenario: Stream an order workflow with optional stages

- **WHEN** 主意图识别结果为 `order` 且订单子图执行多个节点
- **THEN** 事件依次包含开始事件、意图子图及订单子图已完成节点对应的 `THINKING_STEP`，随后发送实际执行阶段的上下文更新（若有）、思考完成和终态事件

#### Scenario: Publish each completed node once

- **WHEN** 子图节点完成并返回状态更新
- **THEN** 系统发送一个对应的节点完成进度事件，事件包含递增 `sequence`，同一节点不得因父图聚合再次重复发送

#### Scenario: Hide order implementation details

- **WHEN** 订单子图执行 rewrite、extract、update_context 或其他内部节点
- **THEN** SSE 可以用稳定节点标识支持客户端映射，但不得把内部调试信息、模型输出或隐藏思维放入 payload

#### Scenario: Stream a minimal order workflow

- **WHEN** 订单子图未启用货物画像或车型处理节点
- **THEN** 系统只发送实际执行的节点和公开阶段事件，不发送虚假的可选节点事件
