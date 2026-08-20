## MODIFIED Requirements

### Requirement: Provide explicit profile fields

每条货物画像 SHALL 包含 `name`、`weight_kg`、`volume_m3`、`dimensions_cm`、`stackability`、`fragility`、`temperature` 和 `reason`。当货物类型与总重量、数量、包装、体积或尺寸中的任意运输规模信息同时存在时，系统 MUST 基于常见单件参数、包装规格、堆积密度和装载方式尽力生成 `weight_kg`、`volume_m3` 和整体 `dimensions_cm` 的具体数值；不得仅因缺少直接尺寸或包装而返回 `null`。`dimensions_cm` 表示整体装车占用尺寸，不是单件尺寸。

#### Scenario: Estimate volume from cargo type and weight

- **WHEN** 用户输入“一吨苹果”，但未提供数量、包装、体积或尺寸
- **THEN** 系统 SHALL 根据苹果常见单件重量、数量推断、包装和装载经验估算总体积及整体占用尺寸，并在 `reason` 中说明推理依据

#### Scenario: Estimate weight and volume from cargo type and quantity

- **WHEN** 用户输入“100箱苹果”，但未提供总重量和总体积
- **THEN** 系统 SHALL 根据常见箱规和单箱重量估算总重量、总体积及整体占用尺寸，并在 `reason` 中说明假设

#### Scenario: Keep null only when transport scale is unknowable

- **WHEN** 用户仅提供货物名称，且没有数量、重量、包装、体积或尺寸等任何运输规模信息
- **THEN** 系统 MAY 将无法估算的核心数值设为 `null`，并在 `reason` 中明确说明本次运输规模无法确定

### Requirement: Explain profile values with one reason

每条画像 SHALL 包含非空字符串 `reason`，解释用户明确值、推导值、基于货物常识的估算值及估算假设。`reason` 不得仅说明“用户未提供”，而必须说明模型尝试使用的物流推理依据；仅在确实没有运输规模信息时说明无法估算的原因。

#### Scenario: Explain forced estimation chain

- **WHEN** 画像使用货物类型和重量推断数量、包装体积及整体尺寸
- **THEN** `reason` SHALL 描述从总重量到单件参数、包装和装车占用空间的主要推理链
