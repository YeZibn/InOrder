# order-entity-extraction Specification

## Purpose

从当前订单解析文本中提取可回溯到原文的结构化实体，为澄清、上下文合并和后续订单处理提供稳定输入，同时明确模型语义决策、字段契约与空结果行为。
## Requirements
### Requirement: Grounded prompt contract

系统 SHALL 使用覆盖全部订单实体及其 attributes 的 grounded prompt 与 few-shot examples，使结构化输出约束允许每个类别和字段。对于 `vehicle_type` 与 `vehicle_specs`，prompt SHALL 要求保留用户本轮原文表达，不得要求 LLM 生成最终 canonical code；车型 catalog 仅作为识别词汇、类别边界和组合拆分的来源。

#### Scenario: Complete schema coverage

- **WHEN** 系统构建订单实体提取请求
- **THEN** 结构化输出约束允许 time、location、person、phone、vehicle_type、vehicle_specs、cargo、follow_car_number、oneself_follow_flag、invoice_type、payment_type、service_type、remark 和 order_id

#### Scenario: Vehicle prompt preserves raw expression
- **WHEN** 用户输入“4米2冷链厢式车”
- **THEN** prompt 约束模型分别提取 `4米2`、`冷链` 和 `厢式` 的原文表达，不要求输出 `truck_4m2`、`cold_chain` 或 `enclosed` code

### Requirement: Grounded source boundary

系统 SHALL 仅从 rewrite 生成的待提取文本生成实体原文；location 的 `full_address` 也 SHALL 仅来自待提取文本中的连续地址原文。reference time 仅用于时间计算，历史对话、订单上下文和输入标题不得作为实体来源。

#### Scenario: Preserve current-turn grounding

- **WHEN** 待提取文本为“再加一吨苹果”
- **THEN** 系统不得从历史订单重新提取起终点等既有实体

#### Scenario: Preserve address source text

- **WHEN** rewrite 文本包含“上海浦东金桥物流园3号仓库”作为装货地址
- **THEN** location 的 `extraction_text` 与 `full_address` 仅来自该待提取文本，不带入上下文中的旧地址

### Requirement: LLM semantic ownership

系统 SHALL 由 LLM 决定实体类别、action、地址 role 和业务 attributes。车型实体的语义职责仅包括识别原文、区分 `vehicle_type`/`vehicle_specs` 并拆分组合表达；canonical vehicle code、模糊车型选择、范围车型解析和历史车型指代 SHALL 不由 extract LLM 最终决定。兼容层只可校验输出契约，不得补全、改写或重判语义。

#### Scenario: Preserve LLM location role

- **WHEN** LLM 输出 location role 为 dropoff
- **THEN** 系统保留该 role，不得因实体顺序改写

#### Scenario: Preserve ambiguous vehicle expression
- **WHEN** 用户输入“小车”或“4米以上”
- **THEN** 系统保留对应原文车型实体，不得在 extract 阶段强制选择单一 canonical vehicle code

### Requirement: Grounded remark representation

系统 SHALL 对 remark 保留用户原文为 extraction_text，并将业务概括放入 attributes.value。

#### Scenario: Grounded fragile remark

- **WHEN** 用户输入“苹果容易碎，轻拿轻放”
- **THEN** remark 的 extraction_text 为该原文，attributes.value 为“易碎轻放”或等价概括

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

### Requirement: Action-annotated entity extraction

系统 SHALL 从用户自然语言输入中提取订单相关实体，每个实体携带 `action` 字段，表示本轮对该实体应用的操作。`action` 取值为 `add`（新增/累加）、`set`（覆盖设置）、`remove`（删除/移除）、`replace`（替换/换成）。

#### Scenario: Add action for incremental input
- **WHEN** 用户输入"再加一吨苹果"
- **THEN** 系统输出实体 `cargo`，`action` 为 `add`，包含 `name:苹果, weight:1吨`

#### Scenario: Set action for initial or override input
- **WHEN** 用户输入"我要两吨苹果"
- **THEN** 系统输出实体 `cargo`，`action` 为 `set`，包含 `name:苹果, weight:2吨`

#### Scenario: Remove action for deletion input
- **WHEN** 用户输入"苹果不要了"
- **THEN** 系统输出实体 `cargo`，`action` 为 `remove`，包含 `name:苹果`

#### Scenario: Replace action for substitution input
- **WHEN** 用户输入"车型换成冷链车"
- **THEN** 系统输出实体 `vehicle_type`，`action` 为 `replace`，包含标准车型 `冷链`

### Requirement: Entity type coverage

系统 SHALL 支持提取以下 14 类实体：time、location、person、phone、vehicle_type、vehicle_specs、cargo、follow_car_number、oneself_follow_flag、invoice_type、payment_type、service_type、remark、order_id。每类实体拥有其各自的属性字段；其中 location 支持 `role`、`city` 和 `full_address`，cargo 支持 `name`、`weight`、`dimensions`、`volume` 和 `quantity`，车型实体至少保留 `extraction_text` 及可选的原始表达属性。

#### Scenario: Location with role extraction
- **WHEN** 用户输入"从上海运到温州"
- **THEN** 系统输出两个 location 实体：`pickup:{city:上海, full_address:上海}` 与 `dropoff:{city:温州, full_address:温州}`

#### Scenario: Location with city and full address

- **WHEN** 用户输入"从上海浦东金桥物流园3号仓库运到温州瓯海批发市场"
- **THEN** 系统输出 pickup 与 dropoff 两个 location 实体，分别包含对应的 `city` 和 `full_address`

#### Scenario: Time with context extraction
- **WHEN** 用户输入"查一下上周的订单"
- **THEN** 系统输出 time 实体，`context:history`，`start/end` 按参考时间换算为绝对时间

#### Scenario: Vehicle type normalization
- **WHEN** 用户输入"来个小面包"
- **THEN** 系统输出 `vehicle_type` 实体，`extraction_text` 为用户原文“小面包”，而不是将其改成“小面”或其他 canonical label

### Requirement: Time semantic normalization

系统 SHALL 将所有相对时间表达按参考时间换算为绝对时间。归一规则：具体时刻 start=end；时段表达按固定区间（上午 06:00-12:00、下午 12:00-18:00、晚上 18:00-23:59）；整日 start=00:00 end=23:59；整月 start=1日00:00 end=末日23:59；开区间"X前"end=参考时间推前；开区间"X后"start=参考时间推后；闭区间"过去X"start=推前end=参考时间；闭区间"未来X"start=参考时间end=推后。

#### Scenario: Relative time to absolute conversion
- **WHEN** 参考时间为 2026-08-14 10:00，用户输入"明天下上午"
- **THEN** 系统输出 time 实体，start=2026-08-15 06:00，end=2026-08-15 12:00

#### Scenario: Open interval before reference time
- **WHEN** 参考时间为 2026-08-14 10:00，用户输入"三天前的订单"
- **THEN** 系统输出 time 实体，context=history，end=2026-08-11 10:00，start 为空（开区间）

### Requirement: Location semantic rules

系统 SHALL 按"从A到B"语义规则确定 location 的 role：A=装货地（pickup）、B=卸货地（dropoff）；"送到X"/"拉到X"→X=卸货地；"到X装货"/"去X取货"→X=装货地。`city` SHALL 仅当用户明确提及城市名时输出，不带"市"后缀；`full_address` SHALL 保存用户本轮明确表达的完整地址，至少包含城市表达，不能通过本地逻辑补全、改写或地理编码。

#### Scenario: From-to location roles
- **WHEN** 用户输入"从上海运货到温州"
- **THEN** 系统输出 pickup:{city:上海, full_address:上海} 和 dropoff:{city:温州, full_address:温州}

#### Scenario: Preserve detailed pickup and dropoff address

- **WHEN** 用户输入"从上海市浦东新区金桥镇某物流园A区3号仓库送到浙江省温州市瓯海区某批发市场"
- **THEN** 系统分别输出 pickup 和 dropoff，保留各自连续原文地址到 `full_address`，并提取明确可识别的 `city`

#### Scenario: Implicit dropoff location
- **WHEN** 用户输入"送到杭州"
- **THEN** 系统输出 dropoff:{city:杭州, full_address:杭州}

#### Scenario: Do not invent missing city or detail

- **WHEN** 用户只输入"从浦东金桥物流园到某批发市场"且无法从文本确定城市
- **THEN** 系统保留用户表达的 `full_address`，不猜测 `city` 或补充行政区信息

### Requirement: Person name splitting

系统 SHALL 将人名拆分为 surname（姓）和 name（名）。示例："老王"→surname=王、name=""；"欧阳夏丹"→surname=欧阳、name=夏丹。person 的 role 为 sender（发货人）或 receiver（收货人），按语义规则推断："X收"/"X签收"→X=receiver；"找X拿"/"X发货"→X=sender。

#### Scenario: Person with role and name splitting
- **WHEN** 用户输入"收货人老王"
- **THEN** 系统输出 person 实体，role=receiver，surname=王，name=""

### Requirement: Vehicle type standardization

系统 SHALL 将车型识别与车型标准化分离。extract 阶段 SHALL 保留用户原文并允许后续归一模块根据车型 catalog 生成 canonical value；extract 阶段不得执行“小拉/轿车”“小面包”“面包车”或“X米以上”等语义归一，也不得以 `extraction_text` 伪装成标准车型值。

#### Scenario: Colloquial vehicle type normalized
- **WHEN** 用户输入"来个面包车"
- **THEN** extract 输出原文 `vehicle_type` 实体“面包车”，并将具体 code 选择留给后续车型归一模块

#### Scenario: Meter-based vehicle type ceiling
- **WHEN** 用户输入"要9米以上的车"
- **THEN** extract 输出原文车型表达“9米以上”及其范围语义，不直接输出 `truck_9m6`

### Requirement: History-aware context tagging

系统 SHALL 当用户引用历史订单时，将相关实体的 context 标记为 history。判断"引用历史订单"需参考对话历史。新需求相关实体 context 为 new_order。

#### Scenario: History reference from conversation
- **WHEN** 对话历史中用户已有下单对话，用户输入"上次那个再发一单"
- **THEN** 系统输出相关实体（如 order_id、time）的 context=history

#### Scenario: New order context by default
- **WHEN** 用户输入"我要从上海运货到温州"
- **THEN** 系统输出 location 等实体的 context=new_order

### Requirement: Extraction input parameters

extract 函数 SHALL 接受三个显式输入参数：`message`（用户本次输入）、`history`（对话历史，结构化消息列表，含 role 和 content）、`reference_time`（参考时间，格式 YYYY-MM-DD HH:MM）。`reference_time` SHALL 在用户消息进入请求边界时确定，并作为本次提取及其格式修复重试的稳定时间锚点；函数不持有会话状态，不依赖全局可变状态。

#### Scenario: Extract with all inputs
- **WHEN** 调用 extract 函数并传入 message、history 和 reference_time
- **THEN** 函数返回带 action 的实体列表

#### Scenario: Empty history allowed
- **WHEN** 调用 extract 函数时 history 为空列表
- **THEN** 函数正常执行，输出不含 history context 的实体

#### Scenario: Request boundary supplies default reference time
- **WHEN** 用户消息进入 CLI 或 HTTP 请求且调用方未提供 reference_time
- **THEN** 请求边界生成当前 Asia/Shanghai 时间，并将非空的 YYYY-MM-DD HH:MM 值传入 extract

#### Scenario: Reuse one reference time during extraction
- **WHEN** 同一次请求需要执行提取、结构化输出修复或重试
- **THEN** 所有调用复用该请求已确定的 reference_time，不在节点或重试过程中重新生成

### Requirement: Structured extraction output

系统 SHALL 将提取后结果转换为统一实体列表。每个实体包含 `extraction_class`、`extraction_text`、`attributes` 和可选 metadata；系统仅可对缺失必填字段、非法 action 枚举或无法读取 grounded 数据等输出契约问题抛出 `StructuredIntentError` 或明确的提取错误，不得因业务语义自行推断或修复输出。

#### Scenario: Valid grounded extraction mapped
- **WHEN** 后端返回可定位的提取结果
- **THEN** 系统将其映射为统一实体，并保留原文片段、attributes 和元数据

#### Scenario: Valid grounded vehicle extraction mapped
- **WHEN** 后端返回车型原文“4.2米”并标记为 `vehicle_type`
- **THEN** 系统映射为统一实体并保留“4.2米”，不在 adapter 中改写为 `truck_4m2`

#### Scenario: Empty extraction is preserved
- **WHEN** 后端返回空提取，无论输入文本看起来是否包含订单信息
- **THEN** 系统 SHALL 返回空实体列表，不得以关键词、正则或其他本地规则将其转换为提取失败或澄清

### Requirement: Extraction backend boundary

系统 SHALL 通过可注入的提取器接口隔离 LangExtract 后端，允许测试替身和后续后端替换；LangGraph 订单节点只依赖该接口，不依赖具体 LangExtract API。

#### Scenario: Injectable extraction backend

- **WHEN** 测试或运行时注入一个实现提取接口的后端
- **THEN** 订单图可以使用该后端完成提取而无需修改图节点
