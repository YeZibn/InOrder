## Why

当前货物画像包含大量 `raw`、`unit`、`basis` 等元数据，结构复杂且不利于直接进行后续车型边界校验。同时，画像允许在存在可合理推断信息时直接返回空值，导致重量、体积和尺寸不足以支持车辆可行性判断。

本次调整将画像收敛为面向车型校验的核心字段，并要求模型在信息足够时尽力估算；只有完全无法估算时才返回 `null`，并用统一的 `reason` 解释依据或缺失原因。

## What Changes

- **BREAKING** 简化货物画像 JSON，移除字段级 `raw`、`unit`、`basis`、`confidence`、`warnings` 及冗余的单件/作用域元数据。
- 保留带单位命名的核心数值：`weight_kg`、`volume_m3`、`dimensions_cm`。
- 保留 `stackability`、`fragility`、`temperature` 三类运输属性。
- 增加必填的 `reason` 字段，说明明确值、估算值及无法估算的原因。
- 规定只有现有信息完全不足以进行合理估算时，核心数值才允许为 `null`。
- 调整画像汇总结构和解析校验，使其与简化后的画像契约一致。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `cargo-profile`: 修改画像字段契约、估算规则和汇总输出要求，为后续车型硬性边界校验提供直接输入。

## Impact

- 影响 `src/inorder_llm/cargo_profile/` 下的 prompt、数据模型、JSON 解析和测试。
- 影响持久化的 `OrderContext.cargo_profiles` 结构；旧画像数据需要按新结构重新生成，不做兼容映射。
- 不实现车型推荐、车型筛选或装箱算法。
