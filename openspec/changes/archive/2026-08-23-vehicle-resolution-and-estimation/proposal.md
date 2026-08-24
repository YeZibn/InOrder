## Why

当前系统已经能够从 `vehicles.json` 归一化用户提供的车型表达，也能够生成货物画像，但两者尚未形成最终车型决策链路。需要明确“用户车型优先、无法匹配才估算”的业务规则，避免系统在用户已经选择明确车型时擅自替换。

## What Changes

- 新增车型解析与估算流程：优先使用用户车型表达在 `vehicles.json` 中的确定性/严格 Ensemble 匹配结果。
- 用户未提供车型，或提供的车型表达无法唯一匹配时，根据完整货物画像估算一个车型。
- 用户车型匹配成功后直接采用 canonical code，不做能力校验、不因货物画像不匹配而替换用户选择。
- 为车型决策结果记录来源，区分用户匹配和系统估算。
- 将车型决策接入订单处理 LangGraph，并在 CLI/结果中展示最终车型及来源。

## Capabilities

### New Capabilities

- `vehicle-resolution-and-estimation`: 根据用户车型表达和货物画像确定最终车型。

### Modified Capabilities

- `order-processing-subgraph`: 在货物画像之后增加车型解析/估算阶段，并返回车型决策结果。
- `cargo-profile`: 保持货物画像不直接选择车型，但允许下游车型估算读取其完整画像和汇总结果。

## Impact

- 影响 `src/inorder_llm/graph/order/`、车型归一化、货物画像结果模型、`OrderContext` 和 CLI 输出。
- 继续使用现有车型主数据、RapidFuzz + n-gram Ensemble 和 JSON 车型能力范围；本变更不实现能力校验。
- 用户明确匹配到的车型不会被估算结果覆盖；模糊或无法匹配的原文保留用于估算原因和诊断。
