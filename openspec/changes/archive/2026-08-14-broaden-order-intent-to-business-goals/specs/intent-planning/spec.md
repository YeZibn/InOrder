## MODIFIED Requirements

### Requirement: Main intent classification

系统 SHALL 将用户请求分类为 `order` 或 `qa` 两种主意图，不再输出 `ambiguous`。判据为用户期望的输出类型而非命令动词：当用户期望的输出是行动/结果（即想让一次运输/订单发生）时归 `order`，当用户期望的输出是信息时归 `qa`。`order` 覆盖业务目标意愿陈述（如运货/发货/配送等），不要求使用创建/下单等显式命令动词。当消息同时携带咨询信号（了解/咨询/怎么/多少钱/能不能/一般 等）时，即使提及业务目标也归 `qa`。意图分类只认用户字面期望输出，深层需求推测不在分类层进行。

#### Scenario: Execution request is order
- **WHEN** 用户使用显式命令要求系统创建、修改或查询订单相关信息
- **THEN** 系统输出主意图 `order`

#### Scenario: Information request is qa
- **WHEN** 用户只是在询问物流、产品、规则、流程或一般知识且没有要求系统执行订单操作
- **THEN** 系统输出主意图 `qa`

#### Scenario: Business goal statement without command is order
- **WHEN** 用户用业务目标语言表达让一次运输/订单发生的意愿但未使用创建/下单等命令动词（如「我想从上海运货到温州」）
- **THEN** 系统输出主意图 `order`

#### Scenario: Business goal with consultation signal is qa
- **WHEN** 用户消息提及业务目标但同时携带咨询信号（如「运货到温州多少钱」「怎么发货」）
- **THEN** 系统输出主意图 `qa`

#### Scenario: Execution takes priority in mixed request
- **WHEN** 用户消息同时包含信息询问和明确的订单执行请求
- **THEN** 系统输出主意图 `order`

#### Scenario: How-to question is qa
- **WHEN** 用户询问“怎么下单”或“订单怎么取消”等操作方法而没有要求代为执行
- **THEN** 系统输出主意图 `qa`

#### Scenario: Capability inquiry is qa despite implied intent
- **WHEN** 用户询问某业务能力或条件是否满足（如「上海到温州能运吗」），即便隐含后续下单可能
- **THEN** 系统输出主意图 `qa`
