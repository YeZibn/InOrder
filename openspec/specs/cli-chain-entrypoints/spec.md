# cli-chain-entrypoints Specification

## Purpose
为 CLI 提供完整链路、意图链路和下单链路三个明确入口，使主意图图与订单处理子图可以独立调试或按顺序组合运行。
## Requirements
### Requirement: Inspect current session context

CLI SHALL 提供只读命令查看当前 session 的结构化订单上下文和会话历史，不改变任何 session 状态。

#### Scenario: Show order context

- **WHEN** 用户输入 `/context`
- **THEN** CLI 以 JSON 形式输出当前 `OrderContext` 的完整可序列化内容

#### Scenario: Show conversation history

- **WHEN** 用户输入 `/conversation`
- **THEN** CLI 以 JSON 形式输出当前 `HistoryConversation` 的有序 turns

#### Scenario: Inspection commands are side-effect free

- **WHEN** 用户执行 `/context` 或 `/conversation`
- **THEN** CLI 不调用任何 graph、不追加 history、不修改 OrderContext

#### Scenario: Empty inspection output

- **WHEN** 当前 session 没有历史或订单字段
- **THEN** CLI 仍返回合法 JSON，分别展示空 turns 和默认空上下文字段

### Requirement: Select one of three CLI chains

系统 SHALL 支持 `full`、`intent` 和 `order` 三种运行链路，并通过统一命令切换当前链路。

#### Scenario: Switch to intent chain

- **WHEN** 用户输入 `/chain intent`
- **THEN** CLI 将当前链路切换为 `intent` 并反馈当前链路

#### Scenario: Switch to order chain

- **WHEN** 用户输入 `/chain order`
- **THEN** CLI 将当前链路切换为 `order` 并反馈当前链路

#### Scenario: Reject unsupported chain

- **WHEN** 用户选择不支持的链路名称
- **THEN** CLI 拒绝切换并提示 `full`、`intent`、`order` 可选值

### Requirement: Route messages by selected chain

CLI SHALL 将普通消息路由到当前链路对应的图入口：`intent` 只调用意图图，`order` 只调用订单处理子图，`full` 先调用意图图并在主意图为 `order` 时继续调用订单处理子图。

#### Scenario: Intent chain invokes only intent graph

- **WHEN** 当前链路为 `intent` 且用户输入普通消息
- **THEN** CLI 调用意图图并输出意图计划，不调用订单处理子图

#### Scenario: Order chain invokes only order graph

- **WHEN** 当前链路为 `order` 且用户输入普通消息
- **THEN** CLI 调用订单处理子图并输出 rewrite、实体和解析状态

#### Scenario: Full chain composes graphs for order

- **WHEN** 当前链路为 `full` 且意图图输出主意图 `order`
- **THEN** CLI 先输出意图计划，再调用订单处理子图并输出订单解析结果

#### Scenario: Full chain does not run order graph for qa

- **WHEN** 当前链路为 `full` 且意图图输出主意图 `qa`
- **THEN** CLI 不调用订单处理子图，并返回问答链路尚未实现的状态

#### Scenario: Full chain completes extraction

- **WHEN** 当前链路为 `full` 且意图图输出主意图 `order`
- **THEN** CLI 输出意图计划、订单处理已进入、rewrite 已完成、extract 已执行和实体数量，并展示提取实体

### Requirement: Expose order processing stage status

full 和 order 链路 SHALL 暴露订单处理阶段状态，至少区分是否进入订单处理子图、rewrite 是否完成、extract 是否执行、最终实体数量，以及订单上下文是否更新。

#### Scenario: Extraction status is observable

- **WHEN** extract 成功返回实体列表
- **THEN** CLI 显示 `extract` 已执行和实体数量

#### Scenario: Context update status is observable

- **WHEN** 订单处理子图返回更新后的订单上下文
- **THEN** CLI 输出订单上下文已更新的状态

### Requirement: Preserve order parsing context

CLI SHALL 为 `order` 和 `full` 链路提供当前消息、`HistoryConversation`、`OrderContext` 和会话级参考时间，并在订单处理子图返回新上下文时保存到当前内存 session。时间锚点 SHALL 按“上下文已有值、调用方提供的有效值、当前 `Asia/Shanghai` 时间”的顺序确定；一旦确定，后续轮次 SHALL 复用该值。Rewrite、Extract 及本轮重试 SHALL 复用同一值。

#### Scenario: Order chain passes context

- **WHEN** 用户在 `order` 链路输入消息
- **THEN** 订单处理子图收到当前历史、订单上下文和参考时间

#### Scenario: Order chain persists updated context

- **WHEN** `order` 链路返回更新后的订单上下文
- **THEN** CLI 将该上下文保存为当前 session 的 `OrderContext`，供下一轮输入使用

#### Scenario: Full chain persists updated context

- **WHEN** `full` 链路识别主意图为 `order` 且订单处理子图返回更新后的订单上下文
- **THEN** CLI 将该上下文保存为当前 session 的 `OrderContext`

#### Scenario: First message creates reference time

- **WHEN** CLI 处理首条消息且当前 `OrderContext.reference_time` 为空
- **THEN** CLI 使用调用方提供的有效时间或当前 Asia/Shanghai 时间生成锚点，并将其写入本轮返回的 `OrderContext`

#### Scenario: Later message reuses context time

- **WHEN** CLI 处理后续消息且当前 `OrderContext.reference_time` 有值
- **THEN** CLI 将该值传入工作流，不重新查询当前时间，也不被后续请求级时间覆盖

#### Scenario: Clear resets conversation state

- **WHEN** 用户输入 `/clear`
- **THEN** CLI 清空消息、历史对话、订单上下文及其 `reference_time`，同时保留当前链路和 CLI 运行状态

### Requirement: Keep compatibility and safe boundary

CLI SHALL 保留 `/intent` 作为切换到 `intent` 链路的兼容命令，并 SHALL 只执行识别、语义解析和内存订单上下文更新；不得执行订单查询、创建或确认。

#### Scenario: Legacy intent command

- **WHEN** 用户输入 `/intent`
- **THEN** CLI 将其解释为查看或切换 `intent` 链路，不破坏既有入口

#### Scenario: Chain output states parsing-only behavior

- **WHEN** 任一链路完成处理
- **THEN** CLI 输出当前链路及解析状态，并明确未执行真实订单业务

### Requirement: Display streaming LLM output

CLI SHALL 在启用流式配置时按增量顺序显示当前 LLM 内容，并在模型调用完成后继续输出原有结构化链路结果；关闭流式配置时 SHALL 保持一次性输出行为。

#### Scenario: Stream within selected chain
- **WHEN** full、intent 或 order 链路触发 LLM 调用且流式展示已启用
- **THEN** CLI 实时显示增量内容，并继续输出对应链路的结构化结果

#### Scenario: Streaming disabled
- **WHEN** 流式配置未启用
- **THEN** CLI 使用现有非流式输出路径，不改变链路选择和业务结果格式

### Requirement: Route full chain through parent graph

CLI SHALL 将 full 链路路由到 MainGraph；intent 和 order 链路 SHALL 继续直接调用各自子图。

#### Scenario: Full chain invokes parent graph
- **WHEN** 当前链路为 `full` 且用户输入普通消息
- **THEN** CLI 调用 MainGraph，由父图编排意图和订单子图

#### Scenario: Independent child chain remains available
- **WHEN** 当前链路为 `intent` 或 `order`
- **THEN** CLI 直接调用对应子图，不要求经过 MainGraph

### Requirement: Recover incomplete conversation turns

CLI 在执行新消息前 SHALL 检查当前 `HistoryConversation` 的末尾是否存在未完成 user 回合；存在时 SHALL 按恢复规则重放或与新消息合并，成功后更新本地 history，失败时保留 pending 状态。

#### Scenario: Retry pending turn
- **WHEN** 上一轮处理失败且 history 末尾只有 user 消息，用户输入“重试”
- **THEN** CLI 只重放该 user 消息并在成功后追加 assistant 摘要

#### Scenario: Merge pending turn with new input
- **WHEN** history 末尾存在 pending user 消息且用户输入新的业务补充
- **THEN** CLI 按原始顺序合并两部分内容，只执行一次工作流
