## MODIFIED Requirements

### Requirement: Check minimum order completeness

系统 SHALL 在订单上下文完成货物画像和车型处理后，检查订单是否具备继续处理所需的最小字段：装货地、卸货地、货物名称、重量或数量至少一个，以及当前订单送达时间。检查 SHALL 基于结构化 `OrderContext` 和其派生字段执行，不调用 LLM 判断字段是否必填；送达时间只根据有效的 start/end 边界判断，不读取或生成 `new_order/history` 上下文。

#### Scenario: Complete minimum order
- **WHEN** 订单上下文包含装货地、卸货地、至少一个货物名称、重量或数量以及有效的送达时间边界
- **THEN** 系统返回 `complete` 状态，缺失必填字段为空，并生成订单事实摘要

#### Scenario: Missing delivery time
- **WHEN** 订单上下文包含路线、货物和重量，但没有有效的送达时间边界
- **THEN** 系统返回 `incomplete` 状态，将送达时间列为必填缺失，并提示用户补充送达时间

#### Scenario: Missing cargo quantity and weight
- **WHEN** 订单上下文包含货物名称，但重量和数量均为空
- **THEN** 系统将重量或数量作为一个组合必填项报告，而不是报告两个重复缺失项

#### Scenario: Incomplete location
- **WHEN** pickup 或 dropoff 对象存在但不包含可用的城市或完整地址
- **THEN** 系统将对应装货地或卸货地报告为缺失，不通过本地规则猜测地址
