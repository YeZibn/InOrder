## MODIFIED Requirements

### Requirement: Estimate when no usable user vehicle exists

当用户未提供车型，或用户车型原文无法唯一匹配车型主数据时，系统 SHALL 根据当前完整货物画像及有效城市目录提供的车型能力字段确定性估算车型，结果来源标记为 `estimated`，并最多返回三个候选；不得调用 LLM 选择车型。系统 SHALL 分别计算各车型范围下界和上界：通过全部下界检查的车型标记为 `lower_bound_fit`，仅通过全部上界检查的车型标记为 `upper_bound_only`。候选 SHALL 先按该等级排序，再在同一等级内优先选择容量较小且够用的车型。只有 `lower_bound_fit` 候选可以作为估算主车型；仅有 `upper_bound_only` 时仍返回候选，但主车型保持为空。有效城市优先取订单起点城市，缺失时取调用方提供的用户定位城市。

#### Scenario: Estimate without a vehicle expression
- **WHEN** 用户只输入货物、重量或数量等订单信息，未提供车型
- **THEN** 系统读取货物画像和车型主数据计算最多三个候选，并将下界通过的候选排在上界通过的候选之前

#### Scenario: Include upper-bound-only recommendations
- **WHEN** 某车型未通过全部下界检查，但通过全部上界检查
- **THEN** 系统将其作为 `upper_bound_only` 推荐候选返回，排在所有 `lower_bound_fit` 候选之后

#### Scenario: Do not promote an upper-bound-only candidate to the primary vehicle
- **WHEN** 没有 `lower_bound_fit` 候选，但存在一个或多个 `upper_bound_only` 候选
- **THEN** 结果 SHALL 返回排序后的上界候选，但 `vehicle_type` SHALL 为空

#### Scenario: Fall back from an ambiguous expression
- **WHEN** 用户输入“大车”“小车”“之前那辆车”或其他无法唯一匹配的车型表达
- **THEN** 系统不强制映射该表达，按上述等级估算候选，并保留原始表达作为决策原因

#### Scenario: Estimate with pickup city catalog
- **WHEN** 用户未提供车型且订单起点城市为温州
- **THEN** 系统使用温州目录进行车型能力和装载评估

#### Scenario: Fall back to user location
- **WHEN** 订单起点城市缺失但用户定位城市为上海
- **THEN** 系统使用上海目录进行车型估算

#### Scenario: Fall back to global data
- **WHEN** 起点城市和用户定位城市均缺失，或城市没有覆盖数据
- **THEN** 系统使用全国默认目录完成车型估算

### Requirement: Preserve unresolved vehicle input

无法匹配的车型原文 SHALL 保留在决策结果或诊断信息中，但不得写入 `OrderContext.vehicle_type` 或 `vehicle_specs` 作为 canonical 值；已有 canonical 车型上下文不得因本次未匹配输入被覆盖。若当前估算没有 `lower_bound_fit` 主候选，系统 SHALL 保留已有 canonical 车型上下文，并将 `upper_bound_only` 候选作为建议单独返回。

#### Scenario: Do not overwrite context with an unresolved vehicle
- **WHEN** 当前上下文已有 `truck_5m2`，本轮输入“换成大车”且“大车”无法唯一匹配，估算只有 `upper_bound_only` 候选
- **THEN** 系统保留当前 canonical 车型和原始“大车”表达，不以仅上界通过的候选覆盖车型字段

### Requirement: Return an explainable resolution result

车型决策结果 SHALL 至少包含最终车型、车型特殊规格（如有）、来源和原因；估算结果还 SHALL 包含 0 至 3 个候选及其 `fit_level` 和排序原因，并记录 `effective_city`、`vehicle_data_source`、目录版本及是否使用过期缓存。`fit_level` SHALL 区分 `lower_bound_fit` 与 `upper_bound_only`；结果不得以无等级的 `fit=true` 将仅上界通过候选表示为下界通过。来源 SHALL 为 `user_matched` 或 `estimated`。

#### Scenario: Report user match source
- **WHEN** 用户车型成功匹配主数据
- **THEN** 结果包含 canonical 车型及 `source="user_matched"`

#### Scenario: Report estimation source and candidate levels
- **WHEN** 车型由货物画像和车型范围推断得到
- **THEN** 结果包含 `source="estimated"`、各候选的 `fit_level` 及相应估算依据

#### Scenario: Report catalog provenance
- **WHEN** 车型由城市目录估算得到
- **THEN** 结果包含有效城市、目录来源、目录版本和过期状态
