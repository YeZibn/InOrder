# cli-chain-entrypoints Specification

## Purpose
为 CLI 提供完整链路、意图链路和下单链路三个明确入口，使主意图图与订单处理子图可以独立调试或按顺序组合运行。
## Requirements
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
- **THEN** CLI 调用订单处理子图并输出 rewrite、实体和澄清状态

#### Scenario: Full chain composes graphs for order

- **WHEN** 当前链路为 `full` 且意图图输出主意图 `order`
- **THEN** CLI 先输出意图计划，再调用订单处理子图并输出订单解析结果

#### Scenario: Full chain does not run order graph for qa

- **WHEN** 当前链路为 `full` 且意图图输出主意图 `qa`
- **THEN** CLI 不调用订单处理子图，并返回问答链路尚未实现的状态

#### Scenario: Full chain completes extraction

- **WHEN** 当前链路为 `full`、意图图输出主意图 `order` 且 rewrite 不需要澄清
- **THEN** CLI 输出意图计划、订单处理已进入、rewrite 已完成、extract 已执行和实体数量，并展示提取实体

#### Scenario: Full chain reports clarification skip

- **WHEN** 当前链路为 `full`、意图图输出主意图 `order` 且 rewrite 返回 `needs_clarification=true`
- **THEN** CLI 输出订单处理已进入、rewrite 已完成、澄清原因和 extract 已跳过，不得让用户误认为实体提取已完成

### Requirement: Expose order processing stage status

full 和 order 链路 SHALL 暴露订单处理阶段状态，至少区分是否进入订单处理子图、rewrite 是否完成、extract 是否执行或跳过，以及最终实体数量。

#### Scenario: Extraction status is observable

- **WHEN** extract 成功返回实体列表
- **THEN** CLI 显示 `extract` 已执行和实体数量

#### Scenario: Skipped extraction status is observable

- **WHEN** rewrite 触发澄清并跳过 extract
- **THEN** CLI 显示 `extract` 已跳过及跳过原因

### Requirement: Preserve order parsing context

CLI SHALL 为 `order` 和 `full` 链路提供当前消息、`HistoryConversation`、`OrderContext` 和参考时间；本次解析不修改订单上下文。

#### Scenario: Order chain passes context

- **WHEN** 用户在 `order` 链路输入消息
- **THEN** 订单处理子图收到当前历史、订单上下文和参考时间

#### Scenario: Clear resets conversation state

- **WHEN** 用户输入 `/clear`
- **THEN** CLI 清空消息、历史对话和订单上下文，同时保留当前链路和 CLI 运行状态

### Requirement: Keep compatibility and safe boundary

CLI SHALL 保留 `/intent` 作为切换到 `intent` 链路的兼容命令，并 SHALL 只执行识别和语义解析，不执行 normalization、reducer、订单查询、创建或确认。

#### Scenario: Legacy intent command

- **WHEN** 用户输入 `/intent`
- **THEN** CLI 将其解释为查看或切换 `intent` 链路，不破坏既有入口

#### Scenario: Chain output states parsing-only behavior

- **WHEN** 任一链路完成处理
- **THEN** CLI 输出当前链路及解析状态，并明确未执行真实订单业务

