## Purpose

为订单工作流提供确定性的完整性判断和业务摘要，使用户能够看到已识别的订单事实、缺失的必要信息以及下一步需要补充的内容。

## ADDED Requirements

### Requirement: Check minimum order completeness

系统 SHALL 在订单上下文完成货物画像和车型处理后，检查订单是否具备继续处理所需的最小字段：装货地、卸货地、货物名称、重量或数量至少一个，以及送达时间。检查 SHALL 基于结构化 `OrderContext` 和其派生字段执行，不调用 LLM 判断字段是否必填。

#### Scenario: Complete minimum order

- **WHEN** 订单上下文包含装货地、卸货地、至少一个货物名称、重量或数量以及有效的送达时间
- **THEN** 系统返回 `complete` 状态，缺失必填字段为空，并生成订单事实摘要

#### Scenario: Missing delivery time

- **WHEN** 订单上下文包含路线、货物和重量，但没有有效的 `delivery_time`
- **THEN** 系统返回 `incomplete` 状态，将送达时间列为必填缺失，并提示用户补充送达时间

#### Scenario: Missing cargo quantity and weight

- **WHEN** 订单上下文包含货物名称，但重量和数量均为空
- **THEN** 系统将重量或数量作为一个组合必填项报告，而不是报告两个重复缺失项

#### Scenario: Incomplete location

- **WHEN** pickup 或 dropoff 对象存在但不包含可用的城市或完整地址
- **THEN** 系统将对应装货地或卸货地报告为缺失，不通过本地规则猜测地址

### Requirement: Distinguish required and optional missing fields

系统 SHALL 将缺失字段分为 `missing_required` 和 `missing_optional`。车型不作为默认必填字段，因为系统可以根据货物画像和车型数据估算；联系人、手机号、备注、支付方式、发票方式等字段是否必填 SHALL 由当前订单阶段的规则配置决定。

#### Scenario: Vehicle can be estimated

- **WHEN** 用户未指定车型但货物信息足以执行车型估算
- **THEN** 系统不因缺少用户车型而将订单标记为不完整，并在摘要中说明车型来自系统估算

#### Scenario: Optional contact information

- **WHEN** 最小订单字段已满足但联系人或手机号为空，且当前阶段未配置为必填
- **THEN** 系统保持 `complete` 状态，并可将联系人信息列入 `missing_optional`

### Requirement: Generate structured business summary

系统 SHALL 同时输出结构化摘要和面向用户的自然语言回复。结构化摘要至少包含订单状态、关键事实、必填缺失字段、可选缺失字段和下一步提示；用户回复 SHALL 使用礼貌、连续、可直接理解的表达，不得直接展示 `complete`、`incomplete`、`missing_required`、内部字段名、节点名称或调试 JSON。回复中的路线、货物、重量、时间和车型 SHALL 只来自订单上下文或车型解析结果，不得由 LLM 编造。

#### Scenario: Summarize a complete order

- **WHEN** 订单完整性检查返回 `complete`
- **THEN** 用户收到类似“已为您整理好这笔运输需求：……订单信息已准备好，可以继续下单”的自然回复；回复包含路线、货物、重量或数量、送达时间和车型（若已解析或估算）

#### Scenario: Summarize an incomplete order

- **WHEN** 订单完整性检查返回 `incomplete`
- **THEN** 用户先看到“目前已为您识别……”等已确认内容，再看到“为了继续为您安排，还需要补充……”等温和提示，并在需要时给出“例如明天下午或 8 月 28 日 10 点”的输入示例

#### Scenario: Preserve structured detail

- **WHEN** 客户端需要调试或后续持久化完整上下文
- **THEN** 结构化摘要与完整 `OrderContext` 独立返回，摘要不得替换或破坏原始订单字段

#### Scenario: Hide technical completeness fields from user reply

- **WHEN** 客户端展示最终用户回复
- **THEN** 回复不出现 `missing_required`、`pickup_location`、`delivery_time`、`incomplete` 等程序字段名，而是使用“装货地”“送达时间”等自然业务名称

### Requirement: Keep summary generation deterministic

系统 SHALL 使用规则生成订单状态、缺失字段、事实摘要和用户回复模板；本次变更不得新增摘要专用 LLM 调用。后续若引入 LLM 语言润色，LLM 只能改写表达，不得改变结构化事实或完整性判断，并必须支持规则回复回退。

#### Scenario: Stable repeated summary

- **WHEN** 相同的订单上下文重复执行完整性检查
- **THEN** 系统返回相同的状态、缺失字段和事实字段，不受模型随机性影响
