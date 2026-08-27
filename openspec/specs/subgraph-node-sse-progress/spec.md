# subgraph-node-sse-progress Specification

## Purpose

为客户端提供子图内部节点完成级别的安全实时进度，让用户能够看到订单工作流持续推进，而无需暴露模型原始输出或内部推理内容。

## Requirements

### Requirement: Emit completed child-node progress

系统 SHALL 在可观测的子图节点完成后发送一条独立的 `THINKING_STEP` SSE 事件，并按实际完成顺序递增携带 `sequence`。事件 SHALL 标明公开业务阶段、节点完成状态和面向用户的安全标题。

#### Scenario: Order child nodes stream independently

- **WHEN** 订单子图依次完成语义重写、实体提取、上下文更新、货物画像、车型处理或订单检查节点
- **THEN** SSE 客户端在每个节点完成后分别收到一条 `THINKING_STEP`，而不是只在订单子图整体完成后收到聚合事件

#### Scenario: Optional node is absent

- **WHEN** 某个可选节点未配置或未被路由执行
- **THEN** 系统不发送该节点的虚假进度事件，其他已执行节点仍按完成顺序发送

### Requirement: Keep node progress safe and stable

节点级进度事件 SHALL 只包含公开阶段、稳定节点标识、完成状态、序号和用户友好标题；不得包含 prompt、原始 LLM 响应、堆栈、隐藏思维或未过滤的内部状态。

#### Scenario: Map internal node to public title

- **WHEN** 客户端收到节点完成事件
- **THEN** 事件提供稳定的公开阶段和用户友好标题，客户端无需依赖模型生成的文本

#### Scenario: Preserve lifecycle compatibility

- **WHEN** 工作流正常完成或失败
- **THEN** 节点级事件仍位于既有 `THINKING_START` 与 `THINKING_DONE`/`DONE` 或单个 `ERROR` 生命周期之间，既有终态字段保持兼容
