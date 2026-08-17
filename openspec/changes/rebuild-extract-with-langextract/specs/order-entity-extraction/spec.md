## MODIFIED Requirements

### Requirement: Order entity extraction

系统 SHALL 从用户本轮订单文本、历史对话和参考时间中提取可定位的订单实体。每个实体 SHALL 包含提取类别、原文片段和 attributes；action SHALL 作为 attributes.action，取值为 `add`、`set`、`remove` 或 `replace`。提取结果还应保留可选的字符位置或对齐元数据，便于验证实体确实来自原文。LLM SHALL 是 action、地址 role、货物字段、车型/规格 code 和其他业务 attributes 的唯一决策方；系统不得根据输入文本或实体顺序补全、覆盖或重判这些字段。

#### Scenario: Extract grounded basic order

- **WHEN** 用户输入“我要两吨苹果从上海运到温州”
- **THEN** 系统至少返回货物“一吨/两吨苹果”、装货地“上海”和卸货地“温州”的原文提取，并在 attributes 中分别写入货物字段、地址 role 和 action

#### Scenario: Extract incremental action in attributes

- **WHEN** 用户输入“再加一吨苹果”
- **THEN** 系统返回 cargo 提取，attributes.action 为 `add`，并包含 name 与 weight

#### Scenario: Extract replacement and removal actions

- **WHEN** 用户输入“苹果改成香蕉，旧车型不要了”
- **THEN** 系统返回对应提取，attributes.action 分别为 `replace` 和 `remove`

#### Scenario: Preserve LLM semantic fields without local inference

- **WHEN** LLM 返回带 attributes 的 grounded entity
- **THEN** 系统原样保留其 action、role 和其他业务 attributes，不得以关键词、正则、实体顺序或默认值改写或补全

### Requirement: Extraction input parameters

extract 函数 SHALL 接受三个显式输入参数：`message`（用户本次输入）、`history`（对话历史，结构化消息列表，含 role 和 content）、`reference_time`（参考时间，格式 YYYY-MM-DD HH:MM）。函数不持有会话状态，不依赖全局可变状态。

#### Scenario: Extract with all inputs

- **WHEN** 调用 extract 函数并传入 message、history 和 reference_time
- **THEN** 函数返回带 attributes.action 的 grounded 实体列表

#### Scenario: Empty history allowed

- **WHEN** history 为空
- **THEN** 函数正常执行，输出不含 history context 的实体

### Requirement: Structured extraction output

系统 SHALL 将提取后结果转换为统一实体列表。每个实体包含 extraction_class、extraction_text、attributes 和可选 metadata；系统仅可对缺失必填字段、非法 action 枚举或无法读取 grounded 数据等输出契约问题抛出 `StructuredIntentError` 或明确的提取错误，不得因业务语义自行推断或修复输出。

#### Scenario: Valid grounded extraction mapped

- **WHEN** 后端返回可定位的提取结果
- **THEN** 系统将其映射为统一实体，并保留原文片段、attributes 和元数据

#### Scenario: Empty extraction is preserved

- **WHEN** 后端返回空提取，无论输入文本看起来是否包含订单信息
- **THEN** 系统 SHALL 返回空实体列表，不得以关键词、正则或其他本地规则将其转换为提取失败或澄清

### Requirement: Extraction backend boundary

系统 SHALL 通过可注入的提取器接口隔离 LangExtract 后端，允许测试替身和后续后端替换；LangGraph 订单节点只依赖该接口，不依赖具体 LangExtract API。

#### Scenario: Injectable extraction backend

- **WHEN** 测试或运行时注入一个实现提取接口的后端
- **THEN** 订单图可以使用该后端完成提取而无需修改图节点
