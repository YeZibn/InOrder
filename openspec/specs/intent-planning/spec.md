# intent-planning Specification

## Purpose

将用户自然语言转换为包含主意图、多子意图及其顺序依赖的结构化 IntentPlan，供后续主图和业务子图进行路由与校验，但不在本能力内执行任何订单或问答操作。

## Requirements

### Requirement: Main intent classification

系统 SHALL 将用户请求分类为 `order`、`qa` 或 `ambiguous` 三种主意图，并在无法可靠区分时使用 `ambiguous`，而不是强行归类。

#### Scenario: Order main intent
- **WHEN** 用户表达创建、修改或参考订单信息的需求
- **THEN** 系统输出主意图 `order`

#### Scenario: QA main intent
- **WHEN** 用户只是在询问物流、产品或一般知识且没有要求执行订单操作
- **THEN** 系统输出主意图 `qa`

#### Scenario: Ambiguous main intent
- **WHEN** 用户请求同时包含无法区分的订单操作和问答诉求
- **THEN** 系统输出主意图 `ambiguous` 并标记需要澄清

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
