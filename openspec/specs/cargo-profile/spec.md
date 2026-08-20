# cargo-profile Specification

## Purpose

为订单货物生成结构化、可解释且可序列化的运输约束画像，为后续重量、体积和车辆可行性校验提供输入，但不直接选择车型。

## Requirements

### Requirement: Generate cargo constraint profiles

系统 SHALL 基于当前完整的原始货物记录调用 LLM 生成货物画像；画像 SHALL 按货物名称对应每种货物，并不得覆盖或改写原始 `cargo` 记录。

#### Scenario: Profile cargo with raw attributes

- **WHEN** 当前货物包含 `name=香蕉`、`weight=["1吨"]` 且其他原始属性为空
- **THEN** 系统返回香蕉画像，并保留原始货物记录不变

#### Scenario: Profile multiple cargo types

- **WHEN** 当前上下文包含苹果和香蕉两种货物
- **THEN** 系统分别返回两条画像，不将不同货物合并为一条画像

### Requirement: Provide explicit profile fields

每条货物画像 SHALL 包含 `name`、`weight_kg`、`volume_m3`、`dimensions_cm`、`stackability`、`fragility`、`temperature` 和 `reason`。当货物类型与总重量、数量、包装、体积或尺寸中的任意运输规模信息同时存在时，系统 MUST 基于常见单件参数、包装规格、堆积密度和装载方式尽力生成 `weight_kg`、`volume_m3` 和整体 `dimensions_cm` 的具体数值；不得仅因缺少直接尺寸或包装而返回 `null`。`weight_kg` 表示本次货物总重量，`volume_m3` 表示预计装车占用总体积，`dimensions_cm` 表示整体装车占用长宽高而不是单件尺寸，所有数值字段使用字段名表达单位，不再要求字段级 `raw`、`unit`、`basis` 或 `confidence` 元数据。

#### Scenario: Profile cargo with sufficient estimation inputs

- **WHEN** 用户提供货物名称及重量、数量、包装或尺寸中的一项或多项足以进行合理估算的信息
- **THEN** 系统 SHALL 尽力生成 `weight_kg`、`volume_m3` 和 `dimensions_cm` 的具体数值，并在 `reason` 中说明明确值或估算依据

#### Scenario: Estimate volume from cargo type and weight

- **WHEN** 用户输入“一吨苹果”，但未提供数量、包装、体积或尺寸
- **THEN** 系统 SHALL 根据苹果常见单件重量、数量推断、包装和装载经验估算总体积及整体占用尺寸，并在 `reason` 中说明推理依据

#### Scenario: Estimate weight and volume from cargo type and quantity

- **WHEN** 用户输入“100箱苹果”，但未提供总重量和总体积
- **THEN** 系统 SHALL 根据常见箱规和单箱重量估算总重量、总体积及整体占用尺寸，并在 `reason` 中说明假设

#### Scenario: Profile cargo with no usable estimation inputs

- **WHEN** 用户仅提供货物名称，且没有数量、重量、包装、体积或尺寸等可用于本次货物规模估算的信息
- **THEN** 系统 SHALL 将无法估算的核心数值设为 `null`，并在 `reason` 中明确说明缺失原因

### Requirement: Classify transport properties

`stackability` SHALL 使用 `full`、`partial`、`none` 或 `unknown`；`fragility` SHALL 使用 `low`、`medium`、`high` 或 `unknown`；`temperature` SHALL 使用 `ambient`、`cool`、`refrigerated`、`frozen` 或 `unknown`。这些属性可以依据货物类型进行合理推断；无法判断时使用 `unknown`，并由 `reason` 说明。

#### Scenario: Infer transport properties from cargo type

- **WHEN** 用户提供了可识别的货物类型但未明确说明运输属性
- **THEN** 系统 SHALL 基于常见物流知识尽力推断堆叠性、易碎性和温度要求，并在 `reason` 中说明这是基于货物类型的判断

### Requirement: Explain profile values with one reason

每条画像 SHALL 包含非空字符串 `reason`，解释用户明确值、推导值、基于货物常识的估算值及估算假设。`reason` 不得仅说明“用户未提供”，而必须说明模型尝试使用的物流推理依据；仅在确实没有运输规模信息时说明无法估算的原因。画像不得再要求字段级 `raw`、`unit`、`basis`、`confidence` 或 `warnings`。

#### Scenario: Explain estimated and unavailable values

- **WHEN** 画像同时包含估算值和无法估算的字段
- **THEN** `reason` SHALL 同时说明估算依据以及无法估算字段的具体原因

#### Scenario: Explain forced estimation chain

- **WHEN** 画像使用货物类型和重量推断数量、包装体积及整体尺寸
- **THEN** `reason` SHALL 描述从总重量到单件参数、包装和装车占用空间的主要推理链

### Requirement: Summarize cargo totals

系统 SHALL 返回当前所有货物的 `total_weight_kg` 和 `total_volume_m3` 汇总；汇总字段 SHALL 使用与画像相同的直接数值表达，不再附带 `weight_status`、`volume_status` 或字段级来源元数据。若任一货物核心数值无法估算，对应汇总值 SHALL 为 `null`，并通过各货物的 `reason` 体现原因。

#### Scenario: Summarize complete estimates

- **WHEN** 当前所有货物均有可用总重量和总体积
- **THEN** 系统 SHALL 返回具体的 `total_weight_kg` 和 `total_volume_m3`

#### Scenario: Partial total remains unavailable

- **WHEN** 至少一种货物的重量或体积完全无法估算
- **THEN** 对应汇总字段 SHALL 返回 `null`，不得生成无依据的替代数值

### Requirement: Replace derived profile atomically

货物画像 SHALL 被视为基于当前完整 `cargo` 的派生数据；当原始货物发生新增、替换或删除时，系统 SHALL 基于完整货物集合重新生成并整体替换画像及汇总，不得按旧画像做增量拼接。

#### Scenario: Rebuild after cargo addition

- **WHEN** 已有苹果画像且原始货物新增一条苹果重量
- **THEN** 系统重新生成苹果画像和汇总，不重复累加旧画像结果

### Requirement: Keep profile generation separate from vehicle selection

画像生成 SHALL 只输出简化后的货物属性和汇总约束，不输出车型推荐、车辆 code、装箱坐标或可行车型结论。

#### Scenario: Profile does not select vehicle

- **WHEN** 系统完成货物画像
- **THEN** 输出不包含 `vehicle_type`、`vehicle_specs`、`recommended_vehicle` 或其他车辆选择字段
