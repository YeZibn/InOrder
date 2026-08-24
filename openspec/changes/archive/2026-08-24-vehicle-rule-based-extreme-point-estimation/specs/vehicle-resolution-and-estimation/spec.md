## MODIFIED Requirements

### Requirement: Estimate when no usable user vehicle exists

当用户未提供车型，或用户车型原文无法唯一匹配车型主数据时，系统 SHALL 根据当前完整货物画像及车型主数据能力字段使用确定性计算估算车型，结果来源标记为 `estimated`，并最多返回三个通过计算的候选车型；不得调用 LLM 选择车型。

#### Scenario: Estimate without a vehicle expression
- **WHEN** 用户只输入货物、重量或数量等订单信息，未提供车型
- **THEN** 系统读取货物画像和车型主数据，通过重量、体积和简化极点装载计算返回最多三个车型候选

#### Scenario: Fall back from an ambiguous expression
- **WHEN** 用户输入“大车”“小车”“之前那辆车”或其他无法唯一匹配的车型表达
- **THEN** 系统不强制映射该表达，使用确定性计算估算最多三个车型，并保留原始表达作为决策原因
