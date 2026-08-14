# intent-planning Specification

## Purpose

将用户自然语言转换为包含主意图、多子意图及其顺序依赖的结构化 IntentPlan，供后续主图和业务子图进行路由与校验，但不在本能力内执行任何订单或问答操作。

## Requirements

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

### Requirement: Multiple order sub-intents

当主意图为 `order` 时，系统 SHALL 支持从单条用户消息中识别零个、一个或多个订单子意图；第一阶段至少支持 `create_order`、`modify_draft` 和 `query_history_order`。

#### Scenario: Single sub-intent
- **WHEN** 用户仅表达创建新订单草稿
- **THEN** 系统输出一个 `create_order` 子意图

#### Scenario: Multiple sub-intents
- **WHEN** 用户要求查询历史订单并将其信息用于修改当前草稿
- **THEN** 系统同时输出 `query_history_order` 和 `modify_draft` 两个子意图

#### Scenario: No recognized sub-intent
- **WHEN** 主意图判断为 `order` 但无法识别具体订单动作
- **THEN** 系统输出空子意图列表并标记需要澄清

### Requirement: Intent plan dependencies

系统 SHALL 为每个子意图生成稳定步骤标识，并表达子意图之间的执行顺序及结果依赖；第一阶段至少支持顺序依赖和 `depends_on` 引用。

#### Scenario: History result feeds draft modification
- **WHEN** 用户要求先查询历史订单，再用历史信息修改当前草稿
- **THEN** 计划将 `query_history_order` 排在 `modify_draft` 之前，并使后者通过 `depends_on` 引用前者

#### Scenario: Independent sub-intents
- **WHEN** 多个子意图之间没有明确的先后或数据引用关系
- **THEN** 计划保留多个独立步骤，不虚构依赖关系

### Requirement: Structured intent plan output

系统 SHALL 输出包含 `main_intent`、`sub_intents`、每个步骤的 `id`、`name`、`arguments`、可选 `depends_on` 以及澄清状态的结构化计划。

#### Scenario: Complete plan
- **WHEN** 用户请求信息完整且意图关系明确
- **THEN** 系统返回可被下游图消费的完整 IntentPlan，并将 `needs_clarification` 设为 false

#### Scenario: Missing information
- **WHEN** 子意图缺少识别所需的关键信息或存在无法消解的歧义
- **THEN** 系统保留已识别信息，设置 `needs_clarification` 为 true，并提供澄清原因

### Requirement: Recognition-only boundary

意图识别子图 SHALL 只负责分类、提取、规范化、关系分析和计划校验，不得查询订单数据、修改草稿、创建订单或调用业务工具。

#### Scenario: Recognition does not execute order operation
- **WHEN** 系统识别出 `query_history_order` 和 `modify_draft`
- **THEN** 系统只返回对应计划，不读取历史订单或写入草稿
