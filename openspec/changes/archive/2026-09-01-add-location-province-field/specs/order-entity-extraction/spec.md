## MODIFIED Requirements

### Requirement: Entity type coverage

系统 SHALL 支持提取以下 13 类当前订单实体：time、location、person、phone、vehicle_type、vehicle_specs、cargo、follow_car_number、oneself_follow_flag、invoice_type、payment_type、service_type 和 remark。每类实体拥有其各自的属性字段；其中 location 支持 `role`、可选的 `province`、`city` 和 `full_address`，cargo 支持 `name`、`weight`、`dimensions`、`volume` 和 `quantity`，time 支持 `start`、`end`，车型实体至少保留 `extraction_text` 及可选的原始表达属性。

#### Scenario: Location with province and city
- **WHEN** 用户输入“从浙江省温州市运到上海市浦东新区”
- **THEN** 系统输出 pickup 的 `province=浙江`、`city=温州`，以及 dropoff 的 `province=上海`、`city=上海`

#### Scenario: Do not infer province
- **WHEN** 用户只输入“温州”且原文没有省级表达
- **THEN** 系统 SHALL 保持 `province=null`，不得根据城市常识补全“浙江”

### Requirement: Location semantic rules

系统 SHALL 按“从A到B”语义规则确定 location 的 role：A=装货地（pickup）、B=卸货地（dropoff）；“送到X”/“拉到X”→X=卸货地；“到X装货”/“去X取货”→X=装货地。`province` 与 `city` SHALL 仅当用户明确提及时输出，不带行政区后缀；`full_address` SHALL 保存用户本轮明确表达的完整地址，至少包含城市表达，不能通过本地逻辑补全、改写或地理编码。

#### Scenario: Preserve explicit province
- **WHEN** 用户输入“浙江省温州市瓯海区某批发市场”
- **THEN** location SHALL 输出 `province=浙江`、`city=温州`，并保留完整连续原文到 `full_address`

#### Scenario: Preserve address source boundary
- **WHEN** 用户输入“从温州装货”且未提及浙江省
- **THEN** location SHALL 输出 `city=温州`、`province=null`，不得将省份补入 `full_address`
