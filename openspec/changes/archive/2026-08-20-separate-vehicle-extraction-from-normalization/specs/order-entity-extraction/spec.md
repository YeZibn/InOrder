## MODIFIED Requirements

### Requirement: Grounded prompt contract

系统 SHALL 使用覆盖全部订单实体及其 attributes 的 grounded prompt 与 few-shot examples，使结构化输出约束允许每个类别和字段。对于 `vehicle_type` 与 `vehicle_specs`，prompt SHALL 要求保留用户本轮原文表达，不得要求 LLM 生成最终 canonical code；车型 catalog 仅作为识别词汇、类别边界和组合拆分的来源。

#### Scenario: Complete schema coverage
- **WHEN** 系统构建订单实体提取请求
- **THEN** 结构化输出约束允许 time、location、person、phone、vehicle_type、vehicle_specs、cargo、follow_car_number、oneself_follow_flag、invoice_type、payment_type、service_type、remark 和 order_id

#### Scenario: Vehicle prompt preserves raw expression
- **WHEN** 用户输入“4米2冷链厢式车”
- **THEN** prompt 约束模型分别提取 `4米2`、`冷链` 和 `厢式` 的原文表达，不要求输出 `truck_4m2`、`cold_chain` 或 `enclosed` code

### Requirement: LLM semantic ownership

系统 SHALL 由 LLM 决定实体类别、action、地址 role 和业务 attributes。车型实体的语义职责仅包括识别原文、区分 `vehicle_type`/`vehicle_specs` 并拆分组合表达；canonical vehicle code、模糊车型选择、范围车型解析和历史车型指代 SHALL 不由 extract LLM 最终决定。兼容层只可校验输出契约，不得补全、改写或重判语义。

#### Scenario: Preserve LLM location role
- **WHEN** LLM 输出 location role 为 dropoff
- **THEN** 系统保留该 role，不得因实体顺序改写

#### Scenario: Preserve ambiguous vehicle expression
- **WHEN** 用户输入“小车”或“4米以上”
- **THEN** 系统保留对应原文车型实体，不得在 extract 阶段强制选择单一 canonical vehicle code

### Requirement: Order entity extraction

系统 SHALL 在提取车型相关实体时区分基础车型/车长与车辆规格：基础车型和车长使用 `vehicle_type`，冷链、厢式、高栏、平板、危险品、高顶和尾板使用 `vehicle_specs`；同一输入中的基础车型和多个规格应分别输出实体，不得把车辆规格归为 `vehicle_type`。车型实体 SHALL 保留用户本轮原文短语，最终 code 由后续独立车型归一阶段生成。

#### Scenario: Extract cold-chain spec
- **WHEN** 用户说“要冷链车”
- **THEN** 系统输出 `vehicle_specs` 实体，`extraction_text` 保留“冷链车”或其中连续原文短语，不在 extract 阶段要求 `cold_chain` code

#### Scenario: Extract combined vehicle and specs
- **WHEN** 用户说“要一辆4米2冷链厢式车”
- **THEN** 系统分别输出 `vehicle_type` 原文“4米2”、`vehicle_specs` 原文“冷链”和 `vehicle_specs` 原文“厢式”三个实体

#### Scenario: Extract multiple vehicle specs separately
- **WHEN** 用户说“4米2高顶带尾板”
- **THEN** 系统输出一个车长实体和两个独立的 `vehicle_specs` 实体，且每个实体保留对应原文

#### Scenario: Preserve range and reference semantics
- **WHEN** 用户输入“9米以上”或“之前那个车”
- **THEN** 系统提取原文车型表达及必要的语义属性，但不得将其改写成某个具体标准车长 code

### Requirement: Entity type coverage

系统 SHALL 支持提取以下 14 类实体：time、location、person、phone、vehicle_type、vehicle_specs、cargo、follow_car_number、oneself_follow_flag、invoice_type、payment_type、service_type、remark、order_id。每类实体拥有其各自的属性字段；其中 location 支持 `role`、`city` 和 `full_address`，cargo 支持 `name`、`weight`、`dimensions`、`volume` 和 `quantity`，车型实体至少保留 `extraction_text` 及可选的原始表达属性。

#### Scenario: Vehicle entity carries source expression
- **WHEN** 用户输入“来个小面包”
- **THEN** 系统输出 `vehicle_type` 实体，`extraction_text` 为用户原文“小面包”，而不是将其改成“小面”或其他 canonical label

### Requirement: Vehicle type standardization

系统 SHALL 将车型识别与车型标准化分离。extract 阶段 SHALL 保留用户原文并允许后续归一模块根据车型 catalog 生成 canonical value；extract 阶段不得执行“小拉/轿车”“小面包”“面包车”或“X米以上”等语义归一，也不得以 `extraction_text` 伪装成标准车型值。

#### Scenario: Defer colloquial vehicle normalization
- **WHEN** 用户输入“来个面包车”
- **THEN** extract 输出原文 `vehicle_type` 实体“面包车”，并将具体 code 选择留给后续车型归一模块

#### Scenario: Defer meter range normalization
- **WHEN** 用户输入“要9米以上的车”
- **THEN** extract 输出原文车型表达“9米以上”及其范围语义，不直接输出 `truck_9m6`

### Requirement: Structured extraction output

系统 SHALL 将提取后结果转换为统一实体列表。每个实体包含 `extraction_class`、`extraction_text`、`attributes` 和可选 metadata；系统仅可对缺失必填字段、非法 action 枚举或无法读取 grounded 数据等输出契约问题抛出 `StructuredIntentError` 或明确的提取错误，不得因业务语义自行推断或修复输出。车型实体的 `extraction_text` 必须可追溯到待提取文本，兼容层不得把原文自动替换为 catalog code。

#### Scenario: Valid grounded vehicle extraction mapped
- **WHEN** 后端返回车型原文“4.2米”并标记为 `vehicle_type`
- **THEN** 系统映射为统一实体并保留“4.2米”，不在 adapter 中改写为 `truck_4m2`

#### Scenario: Empty extraction is preserved
- **WHEN** 后端返回空提取，无论输入文本看起来是否包含订单信息
- **THEN** 系统 SHALL 返回空实体列表，不得以关键词、正则或其他本地规则将其转换为提取失败或澄清
