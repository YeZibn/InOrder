## REMOVED Requirements

### Requirement: Multiple order sub-intents

**Reason**: 子意图不参与父图路由，订单创建和修改由订单实体 action 与订单处理图负责。

**Migration**: 调用方改为读取 `main_intent` 和 `confidence`；订单字段变化通过订单处理结果获取。

### Requirement: Intent plan dependencies

**Reason**: `depends_on` 仅服务于已删除的子意图步骤编排。

**Migration**: 删除步骤依赖校验，后续如需多动作编排再单独设计。

## MODIFIED Requirements

### Requirement: Main intent classification

系统 SHALL 将用户请求分类为 `order` 或 `qa` 两种主意图，不再输出 `ambiguous` 或任何子意图。判据为用户期望的输出类型而非单个关键词：当用户期望系统实际执行运输/订单操作时归 `order`，当用户期望获取物流、产品、规则、流程或一般知识时归 `qa`。当同一消息同时包含明确执行请求与咨询内容时，执行请求优先归 `order`；仅有能力、价格、方法咨询时归 `qa`。

#### Scenario: Execution request is order
- **WHEN** 用户请求系统创建或修改当前订单
- **THEN** 系统输出 `main_intent=order`

#### Scenario: Information request is qa
- **WHEN** 用户只询问信息且没有要求系统执行当前订单操作
- **THEN** 系统输出 `main_intent=qa`

#### Scenario: Polite execution request remains order
- **WHEN** 用户说“可以帮我运一吨苹果吗”
- **THEN** 系统输出 `main_intent=order`，不得仅因“可以吗”判为咨询

#### Scenario: Capability inquiry is qa
- **WHEN** 用户说“上海到温州能运吗”且未要求代为下单
- **THEN** 系统输出 `main_intent=qa`

### Requirement: Main intent structured prompt output

主意图识别 prompt SHALL 要求模型只返回包含 `main_intent` 和 `confidence` 的 JSON 对象，其中 `main_intent` 只能为 `order` 或 `qa`，`confidence` 必须为 0 到 1 之间的数值；识别器不得输出 `sub_intents`、`depends_on` 或澄清字段。

#### Scenario: Strict main-only output
- **WHEN** 主意图识别器处理用户消息
- **THEN** 模型返回合法的 `main_intent` 和范围内的数值 `confidence`，不返回子意图

### Requirement: Clarification boundary

系统 SHALL 不在主意图识别阶段判断订单字段完整性或生成澄清；`order` 与 `qa` 路由完成后，由订单处理图或订单摘要模块负责必要字段检查和用户提示。

#### Scenario: Main classification does not clarify
- **WHEN** 主意图识别器处理任何用户消息
- **THEN** 识别器只返回主意图分类结果，不设置 `needs_clarification`

### Requirement: Structured intent result

系统 SHALL 输出仅包含 `main_intent` 和可选 `confidence` 的主意图结果供父图路由；不得要求或返回 `IntentStep`、`sub_intents`、步骤 id、参数或依赖关系。

#### Scenario: Main intent result is routeable
- **WHEN** 用户输入运输请求或信息咨询
- **THEN** 结果包含可校验的 `main_intent`，父图可据此选择订单或问答分支

### Requirement: Recognition-only boundary

意图识别 SHALL 只负责主意图分类和结果契约校验，不得查询历史订单、修改草稿、创建订单、调用业务工具或执行订单字段合并。

#### Scenario: Recognition does not execute order operation
- **WHEN** 系统识别出 `main_intent=order`
- **THEN** 意图阶段只返回分类结果，订单处理由后续订单图执行
