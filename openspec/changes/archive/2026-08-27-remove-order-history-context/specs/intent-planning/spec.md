## MODIFIED Requirements

### Requirement: Main intent classification

系统 SHALL 将用户请求分类为 `order` 或 `qa` 两种主意图，不再输出 `ambiguous`。判据为用户期望的输出类型而非命令动词：当用户期望的输出是行动/结果（即想让一次运输/订单发生）时归 `order`，当用户期望的输出是信息时归 `qa`。`order` 覆盖当前订单创建和修改，不包含历史订单查询能力。当消息同时携带咨询信号（了解/咨询/怎么/多少钱/能不能/一般 等）时，即使提及业务目标也归 `qa`。

#### Scenario: Execution request is order
- **WHEN** 用户使用显式命令要求系统创建或修改当前订单相关信息
- **THEN** 系统输出主意图 `order`

#### Scenario: Information request is qa
- **WHEN** 用户只是在询问物流、产品、规则、流程或一般知识且没有要求系统执行当前订单操作
- **THEN** 系统输出主意图 `qa`

#### Scenario: Business goal statement without command is order
- **WHEN** 用户用业务目标语言表达让一次运输/订单发生的意愿但未使用创建/下单等命令动词
- **THEN** 系统输出主意图 `order`

#### Scenario: Business goal with consultation signal is qa
- **WHEN** 用户消息提及业务目标但同时携带咨询信号
- **THEN** 系统输出主意图 `qa`

#### Scenario: Execution takes priority in mixed request
- **WHEN** 用户消息同时包含信息询问和明确的当前订单执行请求
- **THEN** 系统输出主意图 `order`

#### Scenario: How-to question is qa
- **WHEN** 用户询问“怎么下单”或“订单怎么取消”等操作方法而没有要求代为执行
- **THEN** 系统输出主意图 `qa`

#### Scenario: Capability inquiry is qa despite implied intent
- **WHEN** 用户询问某业务能力或条件是否满足
- **THEN** 系统输出主意图 `qa`

### Requirement: Multiple order sub-intents

当主意图为 `order` 时，系统 SHALL 支持从单条用户消息中识别零个、一个或多个当前订单子意图；第一阶段支持 `create_order` 和 `modify_draft`，不支持历史订单查询。

#### Scenario: Single sub-intent
- **WHEN** 用户仅表达创建新订单草稿
- **THEN** 系统输出一个 `create_order` 子意图

#### Scenario: Multiple sub-intents
- **WHEN** 用户在同一消息中表达创建或修改当前订单的多个独立动作
- **THEN** 系统输出对应的 `create_order` 或 `modify_draft` 子意图，不生成历史订单子意图

#### Scenario: No recognized sub-intent
- **WHEN** 主意图判断为 `order` 但无法识别具体订单动作
- **THEN** 系统输出空子意图列表并标记需要澄清

### Requirement: Recognition-only boundary

意图识别子图 SHALL 只负责分类、提取、规范化、关系分析和计划校验，不得查询历史订单数据、修改草稿、创建订单或调用业务工具。

#### Scenario: Recognition does not execute order operation
- **WHEN** 系统识别出当前订单的 `create_order` 或 `modify_draft`
- **THEN** 系统只返回对应计划，不读取历史订单或写入草稿
