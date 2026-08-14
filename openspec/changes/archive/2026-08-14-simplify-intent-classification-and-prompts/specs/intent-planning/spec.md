## MODIFIED Requirements

### Requirement: Main intent classification

系统 SHALL 将用户请求分类为 `order` 或 `qa` 两种主意图，不再输出 `ambiguous`。

#### Scenario: Execution request is order
- **WHEN** 用户要求系统创建、修改或查询订单相关信息
- **THEN** 系统输出主意图 `order`

#### Scenario: Information request is qa
- **WHEN** 用户只是在询问物流、产品、规则、流程或一般知识且没有要求系统执行订单操作
- **THEN** 系统输出主意图 `qa`

#### Scenario: Execution takes priority in mixed request
- **WHEN** 用户消息同时包含信息询问和明确的订单执行请求
- **THEN** 系统输出主意图 `order`

#### Scenario: How-to question is qa
- **WHEN** 用户询问“怎么下单”或“订单怎么取消”等操作方法而没有要求代为执行
- **THEN** 系统输出主意图 `qa`

### Requirement: Main intent structured prompt output

主意图识别 prompt SHALL 要求模型只返回包含 `main_intent` 和 `confidence` 的 JSON 对象，其中 `main_intent` 只能为 `order` 或 `qa`。

#### Scenario: Strict JSON classification output
- **WHEN** 主意图识别器处理用户消息
- **THEN** 模型返回仅包含合法 `main_intent` 和数值 `confidence` 的 JSON 对象

### Requirement: Clarification boundary

系统 SHALL 仅在主意图为 `order` 但未识别出具体订单子意图，或订单操作缺少必要信息时设置 `needs_clarification`；主意图分类不得通过 `ambiguous` 状态触发澄清。

#### Scenario: Order without sub-intent needs clarification
- **WHEN** 主意图为 `order` 但没有识别出有效订单子意图
- **THEN** 计划设置 `needs_clarification` 并提供原因

#### Scenario: Main classification does not clarify
- **WHEN** 主意图识别器处理任何用户消息
- **THEN** 识别器只返回 `order` 或 `qa`，不返回 `ambiguous` 或主意图澄清状态
