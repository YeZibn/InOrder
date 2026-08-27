## MODIFIED Requirements

### Requirement: Grounded prompt contract

系统 SHALL 使用覆盖当前订单实体及其 attributes 的 grounded prompt 与 few-shot examples，使结构化输出约束允许每个类别和字段。支持的实体不包含历史订单专用 `order_id`；时间实体只包含 `start`、`end` 及其时间归一化字段，不要求业务上下文标记。对于 `vehicle_type` 与 `vehicle_specs`，prompt SHALL 要求保留用户本轮原文表达，不得要求 LLM 生成最终 canonical code；车型 catalog 仅作为识别词汇、类别边界和组合拆分的来源。

#### Scenario: Complete schema coverage

- **WHEN** 系统构建订单实体提取请求
- **THEN** 结构化输出约束允许 time、location、person、phone、vehicle_type、vehicle_specs、cargo、follow_car_number、oneself_follow_flag、invoice_type、payment_type、service_type 和 remark

#### Scenario: Vehicle prompt preserves raw expression

- **WHEN** 用户输入“4米2冷链厢式车”
- **THEN** prompt 约束模型分别提取 `4米2`、`冷链` 和 `厢式` 的原文表达，不要求输出 canonical code

### Requirement: Order entity extraction

系统 SHALL 在提取车型相关实体时区分基础车型/车长与车辆规格：基础车型和车长使用 `vehicle_type`，冷链、厢式、高栏、平板、危险品、高顶和尾板使用 `vehicle_specs`；同一输入中的基础车型和多个规格应分别输出实体，不得把车辆规格归为 `vehicle_type`。车型实体 SHALL 保留用户本轮原文短语，最终 code 由后续独立车型归一阶段生成。系统不提取历史订单号或历史订单上下文。

#### Scenario: Extract cold-chain spec

- **WHEN** 用户说“要冷链车”
- **THEN** 系统输出 `vehicle_specs` 实体，`extraction_text` 保留“冷链车”或其中连续原文短语，不在 extract 阶段要求 `cold_chain` code

#### Scenario: Extract combined vehicle and specs

- **WHEN** 用户说“要一辆4米2冷链厢式车”
- **THEN** 系统分别输出 `vehicle_type` 原文“4米2”、`vehicle_specs` 原文“冷链”和 `vehicle_specs` 原文“厢式”三个实体

#### Scenario: Extract multiple vehicle specs separately

- **WHEN** 用户说“4米2高顶带尾板”
- **THEN** 系统输出一个车长实体和两个独立的 `vehicle_specs` 实体，且每个实体保留对应原文

#### Scenario: Preserve unresolved vehicle expression

- **WHEN** 用户输入“小车”或“4米以上”
- **THEN** 系统保留对应原文车型表达，不将其改写成具体标准车长 code

### Requirement: Entity type coverage

系统 SHALL 支持提取以下 13 类当前订单实体：time、location、person、phone、vehicle_type、vehicle_specs、cargo、follow_car_number、oneself_follow_flag、invoice_type、payment_type、service_type 和 remark。每类实体拥有其各自的属性字段；其中 location 支持 `role`、`city` 和 `full_address`，cargo 支持 `name`、`weight`、`dimensions`、`volume` 和 `quantity`，time 支持 `start`、`end`，车型实体至少保留 `extraction_text` 及可选的原始表达属性。

#### Scenario: Location with role extraction

- **WHEN** 用户输入"从上海运到温州"
- **THEN** 系统输出两个 location 实体：`pickup:{city:上海, full_address:上海}` 与 `dropoff:{city:温州, full_address:温州}`

#### Scenario: Location with city and full address

- **WHEN** 用户输入"从上海浦东金桥物流园3号仓库运到温州瓯海批发市场"
- **THEN** 系统输出 pickup 与 dropoff 实体，分别包含对应的 `city` 和 `full_address`

#### Scenario: Time extraction without business context

- **WHEN** 用户输入"明天下午三点送达"
- **THEN** 系统输出 time 实体，包含按参考时间换算的 start/end，不包含 `new_order` 或 `history`

#### Scenario: Vehicle type normalization

- **WHEN** 用户输入"来个小面包"
- **THEN** 系统输出 `vehicle_type` 实体，`extraction_text` 为用户原文“小面包”，而不是将其改成“小面”或其他 canonical label

### Requirement: Time semantic normalization

系统 SHALL 将所有相对时间表达按参考时间换算为绝对时间。归一规则：具体时刻 start=end；时段表达按固定区间（上午 06:00-12:00、下午 12:00-18:00、晚上 18:00-23:59）；整日 start=00:00 end=23:59；整月 start=1日00:00 end=末日23:59；开区间"X前"end=参考时间推前；开区间"X后"start=参考时间推后；闭区间"过去X"start=推前end=参考时间；闭区间"未来X"start=参考时间end=推后。时间结果只服务于当前订单送达时间，不区分订单或历史查询上下文。

#### Scenario: Relative time to absolute conversion

- **WHEN** 参考时间为 2026-08-14 10:00，用户输入"明天下午"
- **THEN** 系统输出 time 实体，start=2026-08-15 12:00，end=2026-08-15 18:00，且不包含业务上下文字段

#### Scenario: Open interval before reference time

- **WHEN** 参考时间为 2026-08-14 10:00，用户输入"三天前"
- **THEN** 系统输出 time 实体，end=2026-08-11 10:00，start 为空，且不包含历史查询标记

## REMOVED Requirements

### Requirement: History-aware context tagging

**Reason**：当前版本不实现历史订单查询、历史订单时间或历史订单实体标记。

**Migration**：保留 `HistoryConversation` 作为当前会话消息输入，但所有提取实体均按当前订单语义处理。
