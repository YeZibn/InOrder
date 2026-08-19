## MODIFIED Requirements

### Requirement: Entity type coverage

系统 SHALL 支持提取以下 14 类实体：time、location、person、phone、vehicle_type、vehicle_specs、cargo、follow_car_number、oneself_follow_flag、invoice_type、payment_type、service_type、remark、order_id。每类实体拥有其各自的属性字段；其中 `location` SHALL 支持 `role`、`city` 和 `full_address`。

#### Scenario: Location with city and full address

- **WHEN** 用户输入“从上海浦东金桥物流园3号仓库运到温州瓯海批发市场”
- **THEN** 系统输出 pickup 与 dropoff 两个 location 实体，分别包含对应的 `city` 和 `full_address`

#### Scenario: Location without detailed address

- **WHEN** 用户输入“从上海运到温州”
- **THEN** 系统输出 pickup `{city:上海, full_address:上海}` 与 dropoff `{city:温州, full_address:温州}`，不额外猜测地址细节

### Requirement: Location semantic rules

系统 SHALL 按“从A到B”语义规则确定 location 的 role：A=装货地（pickup）、B=卸货地（dropoff）；“送到X”/“拉到X”→X=卸货地；“到X装货”/“去X取货”→X=装货地。`city` SHALL 仅在用户明确提及城市时输出；`full_address` SHALL 保存用户本轮明确表达的完整地址，至少包含城市表达，不能通过本地逻辑补全、改写或地理编码。

#### Scenario: Preserve detailed pickup and dropoff address

- **WHEN** 用户输入“从上海市浦东新区金桥镇某物流园A区3号仓库送到浙江省温州市瓯海区某批发市场”
- **THEN** 系统分别输出 pickup 和 dropoff，保留各自连续原文地址到 `full_address`，并提取明确可识别的 `city`

#### Scenario: Do not invent missing city or detail

- **WHEN** 用户只输入“从浦东金桥物流园到某批发市场”且无法从文本确定城市
- **THEN** 系统保留用户表达的 `full_address`，不猜测 `city` 或补充行政区信息

### Requirement: Grounded source boundary

系统 SHALL 仅从 rewrite 生成的待提取文本生成 location 的 `extraction_text` 和 `full_address` 原文；reference time、历史对话、订单上下文和输入标题不得作为地址来源。

#### Scenario: Preserve address source text

- **WHEN** rewrite 文本包含“上海浦东金桥物流园3号仓库”作为装货地址
- **THEN** location 的 `extraction_text` 与 `full_address` 仅来自该待提取文本，不带入上下文中的旧地址
