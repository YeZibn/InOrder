## MODIFIED Requirements

### Requirement: Provide explicit profile fields

每条货物画像 SHALL 只包含面向后续车型校验的核心属性：`name`、`weight_kg`、`volume_m3`、`dimensions_cm`、`stackability`、`fragility`、`temperature` 和 `reason`。`weight_kg` 表示本次货物总重量，`volume_m3` 表示预计装车占用总体积，`dimensions_cm` 表示整体占用长宽高，所有数值字段使用字段名表达单位，不再要求字段级 `raw`、`unit`、`basis` 或 `confidence` 元数据。

#### Scenario: Profile cargo with sufficient estimation inputs

- **WHEN** 用户提供货物名称及重量、数量、包装或尺寸中的一项或多项足以进行合理估算的信息
- **THEN** 系统 SHALL 尽力生成 `weight_kg`、`volume_m3` 和 `dimensions_cm` 的具体数值，并在 `reason` 中说明明确值或估算依据

#### Scenario: Profile cargo with no usable estimation inputs

- **WHEN** 用户仅提供货物名称，且没有数量、重量、包装、体积或尺寸等可用于本次货物规模估算的信息
- **THEN** 系统 SHALL 将无法估算的核心数值设为 `null`，并在 `reason` 中明确说明缺失原因

### Requirement: Classify transport properties

`stackability` SHALL 使用 `full`、`partial`、`none` 或 `unknown`；`fragility` SHALL 使用 `low`、`medium`、`high` 或 `unknown`；`temperature` SHALL 使用 `ambient`、`cool`、`refrigerated`、`frozen` 或 `unknown`。这些属性可以依据货物类型进行合理推断；无法判断时使用 `unknown`，并由 `reason` 说明。

#### Scenario: Infer transport properties from cargo type

- **WHEN** 用户提供了可识别的货物类型但未明确说明运输属性
- **THEN** 系统 SHALL 基于常见物流知识尽力推断堆叠性、易碎性和温度要求，并在 `reason` 中说明这是基于货物类型的判断

### Requirement: Explain profile values with one reason

每条画像 SHALL 包含非空字符串 `reason`。该字段 SHALL 解释核心数值和运输属性是用户明确提供、基于信息推导、基于常识估算，还是因信息不足无法确定。画像不得再要求字段级 `raw`、`unit`、`basis`、`confidence` 或 `warnings`。

#### Scenario: Explain estimated and unavailable values

- **WHEN** 画像同时包含估算值和无法估算的字段
- **THEN** `reason` SHALL 同时说明估算依据以及无法估算字段的具体原因

### Requirement: Summarize cargo totals

系统 SHALL 返回当前所有货物的 `total_weight_kg` 和 `total_volume_m3` 汇总；汇总字段 SHALL 使用与画像相同的直接数值表达，不再附带 `weight_status`、`volume_status` 或字段级来源元数据。若任一货物核心数值无法估算，对应汇总值 SHALL 为 `null`，并通过各货物的 `reason` 体现原因。

#### Scenario: Summarize complete estimates

- **WHEN** 当前所有货物均有可用总重量和总体积
- **THEN** 系统 SHALL 返回具体的 `total_weight_kg` 和 `total_volume_m3`

#### Scenario: Partial total remains unavailable

- **WHEN** 至少一种货物的重量或体积完全无法估算
- **THEN** 对应汇总字段 SHALL 返回 `null`，不得生成无依据的替代数值

### Requirement: Keep profile generation separate from vehicle selection

画像生成 SHALL 只输出简化后的货物属性和汇总约束，不输出车型推荐、车辆 code、装箱坐标或可行车型结论。

#### Scenario: Profile does not select vehicle

- **WHEN** 系统完成货物画像
- **THEN** 输出不包含 `vehicle_type`、`vehicle_specs`、`recommended_vehicle` 或其他车辆选择字段
