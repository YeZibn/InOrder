## ADDED Requirements

### Requirement: Grounded prompt contract

系统 SHALL 使用覆盖完整订单实体范围的 grounded prompt 和 few-shot examples。每个支持的实体类别及其允许的 attributes SHALL 至少出现在一个 example 中，使结构化输出约束允许该类别和字段；prompt SHALL 明确原文定位、输入边界、action 语义和空提取行为。

#### Scenario: Complete schema coverage

- **WHEN** 系统构建订单实体提取请求
- **THEN** 结构化输出约束允许 time、location、person、phone、vehicle_type、vehicle_specs、cargo、follow_car_number、oneself_follow_flag、invoice_type、payment_type、service_type、remark 和 order_id

#### Scenario: Empty extraction

- **WHEN** 模型未从待提取文本识别到订单实体
- **THEN** 系统返回空实体列表，不得以关键词、正则或默认值改判为失败或澄清

### Requirement: Grounded source boundary

系统 SHALL 将 reference time 仅用于相对时间计算，并仅允许从待提取文本生成实体的原文片段。历史对话、订单上下文、输入分段标题和参考时间文本不得成为实体原文来源。

#### Scenario: Preserve current-turn grounding

- **WHEN** 历史对话包含“上海到温州”的旧订单，待提取文本为“再加一吨苹果”
- **THEN** 系统仅返回 extraction_text 可定位到“再加一吨苹果”的实体，不得重新提取上海或温州

### Requirement: LLM semantic ownership

系统 SHALL 由 LLM 决定实体类别、action、地址 role、业务 attributes 和规范 code。兼容层可以校验结构化输出契约，但不得根据关键词、实体顺序、历史内容或默认值补全、改写或重判 LLM 的语义输出。

#### Scenario: Preserve LLM location role

- **WHEN** LLM 输出 location，attributes.role 为 dropoff
- **THEN** 系统保留 dropoff，不得因实体在列表中的位置改为 pickup

### Requirement: Grounded remark representation

系统 SHALL 对 remark 保留用户原文片段作为 extraction_text，并将简短业务概括放在 attributes.value。

#### Scenario: Grounded fragile remark

- **WHEN** 用户输入“苹果容易碎，轻拿轻放”
- **THEN** remark 的 extraction_text 为该用户原文片段，attributes.value 为“易碎轻放”或等价概括

## MODIFIED Requirements

### Requirement: Action-annotated entity extraction

系统 SHALL 从用户自然语言输入中提取订单相关实体，每个实体在 attributes 中携带 `action` 字段，表示本轮对该实体应用的操作。`action` 取值为 `add`（新增/累加）、`set`（覆盖设置）、`remove`（删除/移除）、`replace`（替换/换成），并由 LLM 直接决定。

#### Scenario: Add action for incremental input
- **WHEN** 用户输入“再加一吨苹果”
- **THEN** 系统输出 cargo，attributes.action 为 `add`，包含 `name: 苹果, weight: 1吨`

#### Scenario: Set action for initial or override input
- **WHEN** 用户输入“我要两吨苹果”
- **THEN** 系统输出 cargo，attributes.action 为 `set`，包含 `name: 苹果, weight: 2吨`

#### Scenario: Remove action for deletion input
- **WHEN** 用户输入“苹果不要了”
- **THEN** 系统输出 cargo，attributes.action 为 `remove`，包含 `name: 苹果`

#### Scenario: Replace action for substitution input
- **WHEN** 用户输入“车型换成冷链车”
- **THEN** 系统输出 vehicle_specs，attributes.action 为 `replace`，包含规范值 `cold_chain`

### Requirement: Entity type coverage

系统 SHALL 支持提取以下 14 类实体：time、location、person、phone、vehicle_type、vehicle_specs、cargo、follow_car_number、oneself_follow_flag、invoice_type、payment_type、service_type、remark、order_id。每类实体拥有其各自的属性字段；所有类别和属性字段 SHALL 由 grounded examples 覆盖，确保其可作为结构化输出返回。

#### Scenario: Location with role extraction
- **WHEN** 用户输入“从上海运到温州”
- **THEN** 系统输出两个 location 实体，分别带 attributes.role=`pickup`、city=`上海` 与 attributes.role=`dropoff`、city=`温州`

#### Scenario: Time with context extraction
- **WHEN** 用户输入“查一下上周的订单”
- **THEN** 系统输出 time 实体，attributes.context=`history`，start/end 按参考时间换算为绝对时间

#### Scenario: Vehicle type normalization
- **WHEN** 用户输入“来个小面包”
- **THEN** 系统输出 vehicle_type，extraction_text 保留“小面包”，attributes.value 为 `small_van`

### Requirement: Extraction input parameters

实体提取 SHALL 接收 rewrite 生成的待提取文本与 reference time。历史对话和 OrderContext SHALL 由 rewrite 阶段消费，不得作为实体提取阶段的业务语义输入。

#### Scenario: Extract rewritten text with reference time
- **WHEN** 调用方提供 rewrite 的 extraction text 与 reference time
- **THEN** 系统基于该文本提取实体，并使用 reference time 解析相对时间

#### Scenario: History resolved before extraction
- **WHEN** 用户输入依赖历史对话或订单上下文的指代
- **THEN** rewrite 先将其消解为明确的 extraction text，实体提取不直接读取历史或 OrderContext

### Requirement: Structured extraction output

系统 SHALL 将 grounded 结构化结果转换为实体列表。每个实体包含 extraction class、原文 extraction text、attributes 和可选定位 metadata；attributes.action 必须是合法 action。缺少必填结构、非法 action 或无法读取 grounded 数据时 SHALL 抛出结构化提取错误。

#### Scenario: Valid grounded result parsed to entities
- **WHEN** 模型返回合法的 grounded 结构化输出
- **THEN** 系统解析为实体列表，每个实体保留类别、action、attributes、原文片段和可选定位 metadata

#### Scenario: Invalid grounded output raises error
- **WHEN** 模型返回缺少 attributes.action 或包含非法 action 的实体
- **THEN** 系统抛出结构化提取错误，不使用默认 action 修复结果
