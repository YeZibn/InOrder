# intent-planning Specification

## Purpose

将用户自然语言转换为主意图分类结果，供后续主图进行路由与校验，但不在本能力内执行任何订单或问答操作。

## Requirements

### Requirement: Main intent classification

系统 SHALL 将用户请求分类为 `order` 或 `qa` 两种主意图，不再输出 `ambiguous` 或任何子意图。分类判据是用户期望的输出类型而非单个关键词：当用户期望系统实际执行运输或当前订单操作时归 `order`；当用户期望获取物流、产品、规则、流程或一般知识时归 `qa`。`order` 覆盖当前订单创建和修改，不包含历史订单查询能力。同一消息同时包含明确执行请求和咨询内容时，执行请求优先归 `order`；仅询问能力、价格或操作方法时归 `qa`。

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
- **WHEN** 用户消息提及业务目标并携带咨询信号，但未明确要求系统执行当前订单操作
- **THEN** 系统输出主意图 `qa`

#### Scenario: Execution takes priority in mixed request
- **WHEN** 用户消息同时包含信息询问和明确的当前订单执行请求
- **THEN** 系统输出主意图 `order`

#### Scenario: How-to question is qa
- **WHEN** 用户询问“怎么下单”或“订单怎么取消”等操作方法而没有要求代为执行
- **THEN** 系统输出主意图 `qa`

#### Scenario: Capability inquiry is qa despite implied intent
- **WHEN** 用户询问“上海到温州能运吗”且未要求代为下单
- **THEN** 系统输出主意图 `qa`

#### Scenario: Polite execution request remains order
- **WHEN** 用户说“可以帮我运一吨苹果吗”
- **THEN** 系统输出 `main_intent=order`，不得仅因“可以吗”判为咨询

### Requirement: Main intent structured prompt output

主意图识别 prompt SHALL 要求模型只返回包含 `main_intent` 和 `confidence` 的 JSON 对象，其中 `main_intent` 只能为 `order` 或 `qa`，`confidence` 必须为 0 到 1 之间的数值；不得返回 `sub_intents`、`depends_on` 或澄清字段。

#### Scenario: Strict JSON classification output
- **WHEN** 主意图识别器处理用户消息
- **THEN** 模型返回仅包含合法 `main_intent` 和数值 `confidence` 的 JSON 对象

### Requirement: Clarification boundary

系统 SHALL 不在主意图识别阶段判断订单字段完整性或生成澄清；完成 `order`/`qa` 路由后，由订单处理图或订单摘要模块负责必要字段检查和用户提示，主意图分类不得通过 `ambiguous` 状态触发澄清。

#### Scenario: Main classification does not clarify
- **WHEN** 主意图识别器处理任何用户消息
- **THEN** 识别器只返回 `order` 或 `qa`，不返回 `ambiguous` 或主意图澄清状态

### Requirement: Structured intent result

系统 SHALL 输出包含 `main_intent` 和可选 `confidence` 的主意图结果供父图路由，不得要求或返回 `IntentStep`、`sub_intents`、步骤 id、参数或依赖关系。

#### Scenario: Complete main intent result
- **WHEN** 用户输入运输请求或信息咨询
- **THEN** 系统返回可被下游图消费的主意图结果

### Requirement: Recognition-only boundary

意图识别子图 SHALL 只负责主意图分类和结果契约校验，不得查询历史订单数据、修改草稿、创建订单、调用业务工具或执行订单字段合并。

#### Scenario: Recognition does not execute order operation
- **WHEN** 系统识别出 `main_intent=order`
- **THEN** 系统只返回分类结果，不读取历史订单或写入草稿
