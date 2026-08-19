## Purpose

为订单货物生成结构化、可解释且可序列化的运输约束画像，为后续重量、体积和车辆可行性校验提供输入，但不直接选择车型。

## ADDED Requirements

### Requirement: Generate cargo constraint profiles

系统 SHALL 基于当前完整的原始货物记录调用 LLM 生成货物画像；画像 SHALL 按货物名称对应每种货物，并不得覆盖或改写原始 `cargo` 记录。

#### Scenario: Profile cargo with raw attributes

- **WHEN** 当前货物包含 `name=香蕉`、`weight=["1吨"]` 且其他原始属性为空
- **THEN** 系统返回香蕉画像，并保留原始货物记录不变

#### Scenario: Profile multiple cargo types

- **WHEN** 当前上下文包含苹果和香蕉两种货物
- **THEN** 系统分别返回两条画像，不将不同货物合并为一条画像

### Requirement: Provide explicit profile fields

每条货物画像 SHALL 包含 `name`、`quantity`、`weight`、`dimensions`、`volume`、`stackability`、`fragility` 和 `temperature` 字段。`quantity` SHALL 支持数量值和单位；`weight` SHALL 支持总重量和可选单件重量；`dimensions` SHALL 区分单件或整体尺寸；`volume` SHALL 支持单件体积和本次货物总体积。

#### Scenario: Profile dimensions and volume

- **WHEN** 用户提供货物尺寸或体积
- **THEN** 画像保留对应字段，并明确尺寸作用域和体积是明确值、推导值还是估算值

#### Scenario: Unknown field remains explicit

- **WHEN** 信息不足以可靠推断某个字段
- **THEN** 该字段使用 `null` 或 `unknown`，不得生成无依据的精确值

### Requirement: Classify transport properties

`stackability.value` SHALL 使用 `full`、`partial`、`none` 或 `unknown`；`fragility.value` SHALL 使用 `low`、`medium`、`high` 或 `unknown`；`temperature.requirement` SHALL 使用 `ambient`、`cool`、`refrigerated`、`frozen` 或 `unknown`。每个推断属性 SHALL 可附带置信度和理由。

#### Scenario: Preserve fragile and cold requirements

- **WHEN** 用户明确说明货物易碎且需要冷藏
- **THEN** 画像分别标记高易碎性和 `refrigerated`，并保留对应依据

### Requirement: Track profile provenance and uncertainty

每个数值或枚举画像字段 SHALL 标注 `basis`（`explicit`、`estimated`、`derived` 或 `unknown`）和 `confidence`（`high`、`medium` 或 `low`，未知时允许为 `unknown`）。LLM 估算 SHALL 记录 `assumptions`；不确定或冲突信息 SHALL 记录 `warnings`。

#### Scenario: Estimated volume includes assumptions

- **WHEN** 只有货物名称和重量，体积需要根据常见包装估算
- **THEN** 画像标记 `basis=estimated`，包含置信度，并列出估算假设

#### Scenario: Conflicting raw facts are surfaced

- **WHEN** 原始货物表达无法判断是增量重量还是同一重量的重复描述
- **THEN** 系统不擅自相加，并在画像或汇总中返回 warning

### Requirement: Summarize cargo totals

系统 SHALL 返回当前所有货物的 `total_weight_kg` 和预计装车占用 `total_volume_m3` 汇总，并为每个汇总值标注状态和置信度。无法可靠汇总时 SHALL 返回 `null` 或 `partial` 状态及警告。

#### Scenario: Summarize complete estimates

- **WHEN** 每种货物均有可用重量和体积画像
- **THEN** 系统返回总重量和总体积，并保留各字段的来源状态

#### Scenario: Partial total remains uncertain

- **WHEN** 至少一种货物缺少可靠体积
- **THEN** 总体积状态为 `partial` 或 `unknown`，不得伪装成精确总体积

### Requirement: Replace derived profile atomically

货物画像 SHALL 被视为基于当前完整 `cargo` 的派生数据；当原始货物发生新增、替换或删除时，系统 SHALL 基于完整货物集合重新生成并整体替换画像及汇总，不得按旧画像做增量拼接。

#### Scenario: Rebuild after cargo addition

- **WHEN** 已有苹果画像且原始货物新增一条苹果重量
- **THEN** 系统重新生成苹果画像和汇总，不重复累加旧画像结果

### Requirement: Keep profile generation separate from vehicle selection

画像生成 SHALL 只输出货物属性和汇总约束，不输出车型推荐、车辆 code、装箱坐标或可行车型结论。

#### Scenario: Profile does not select vehicle

- **WHEN** 系统完成货物画像
- **THEN** 输出不包含 `vehicle_type`、`vehicle_specs` 或推荐车型字段
