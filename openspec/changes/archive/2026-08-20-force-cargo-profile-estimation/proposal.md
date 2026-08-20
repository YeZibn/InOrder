## Why

当前货物画像在“已知货物类型 + 总重量”时仍可能将总体积和尺寸返回为 `null`，导致后续车型空间边界校验失去输入。物流画像的目标是形成可用于初筛的约束，因此需要强制利用货物常识、单件参数、包装和装载经验完成估算。

## What Changes

- **BREAKING** 收紧核心字段为空的条件：已知货物类型与任意运输规模信息时，必须尽力估算重量、总体积和整体占用尺寸。
- 在 prompt 中加入基于货物类型、总重量、数量、包装、密度和装载方式的推理链要求。
- 明确 `dimensions_cm` 是整体装车占用尺寸，不是单件尺寸。
- 保留 `reason`，要求解释估算依据；只有货物规模完全无法确定时才允许核心字段为 `null`。
- 增加苹果等典型货物的估算测试场景。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `cargo-profile`: 修改核心数值估算和 `null` 返回条件。

## Impact

- 影响 `src/inorder_llm/cargo_profile/resolver.py` 的 prompt 和相关测试。
- 不改变车型推荐、车型筛选或装箱算法边界。
- 估算值仍由 LLM 生成，本地解析器只负责结构和数值合法性校验。
