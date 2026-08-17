## MODIFIED Requirements

### Requirement: Intent mode selection

系统 SHALL 支持通过 `/chain [full|intent|order]` 选择运行链路，并保留 `/intent` 作为切换到 `intent` 链路的兼容命令；当前 CLI 状态 SHALL 显示所选链路。

#### Scenario: Direct chain switch

- **WHEN** 用户输入 `/chain order`
- **THEN** 系统将当前链路切换为 `order` 并反馈新链路

#### Scenario: Direct mode switch

- **WHEN** 用户输入 `/intent order`
- **THEN** 系统将当前模式切换为 `order` 并反馈新模式

#### Scenario: Interactive chain switch

- **WHEN** 用户输入不带参数的 `/chain`
- **THEN** 系统展示 `full`、`intent`、`order` 可选链路并根据用户选择切换

#### Scenario: Interactive mode switch

- **WHEN** 用户输入不带参数的 `/intent`
- **THEN** 系统展示可选模式并根据用户选择切换模式

#### Scenario: Legacy intent alias

- **WHEN** 用户输入 `/intent`
- **THEN** 系统保留兼容行为并切换或提示 `intent` 链路

#### Scenario: Invalid chain

- **WHEN** 用户输入未支持的链路
- **THEN** 系统拒绝切换并提示合法链路

#### Scenario: Invalid mode

- **WHEN** 用户输入未支持的模式
- **THEN** 系统拒绝切换并提示合法模式

### Requirement: Mode to graph routing

系统 SHALL 将当前链路映射到明确处理入口：`intent` 调用意图图，`order` 调用订单处理子图，`full` 组合调用两者；旧的 `auto`、`qa`、`plan` 模式不再作为三条链路的主选择项。

#### Scenario: Intent chain

- **WHEN** 当前链路为 `intent` 且用户输入普通消息
- **THEN** 系统调用意图图并输出意图计划

#### Scenario: Order chain

- **WHEN** 当前链路为 `order` 且用户输入普通消息
- **THEN** 系统调用订单处理子图并输出订单解析结果

#### Scenario: Full chain

- **WHEN** 当前链路为 `full` 且用户输入普通消息
- **THEN** 系统按主意图结果决定是否继续调用订单处理子图

#### Scenario: Full chain exposes order processing status

- **WHEN** full 链路进入订单处理子图
- **THEN** 系统输出订单处理是否进入、rewrite 是否完成、extract 是否执行或跳过、跳过原因和实体数量

#### Scenario: Auto mode

- **WHEN** 当前模式为 `auto` 且用户输入普通消息
- **THEN** 系统调用完整链路

#### Scenario: Plan mode

- **WHEN** 当前模式为 `plan` 且用户输入普通消息
- **THEN** 系统输出结构化意图计划
