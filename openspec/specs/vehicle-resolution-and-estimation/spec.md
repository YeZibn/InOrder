## Purpose

为订单提供遵循用户明确车型选择的最终车型解析，并在缺少可用用户车型时利用货物画像估算车型，形成可解释且不擅自替换用户选择的决策结果。

## Requirements

### Requirement: Prefer a matched user vehicle

系统 SHALL 先使用用户本轮或当前上下文中的车型表达匹配集中车型主数据；匹配成功时 SHALL 直接采用 canonical `vehicle_type` 和 `vehicle_specs`，并将结果来源标记为 `user_matched`。匹配成功的用户车型不得被货物画像估算结果替换。

#### Scenario: Resolve an exact user vehicle
- **WHEN** 用户输入“用4米2厢式车”且车型表达可匹配主数据
- **THEN** 系统采用 `vehicle_type=truck_4m2`、`vehicle_specs=["enclosed"]`，来源为 `user_matched`

#### Scenario: Keep a matched vehicle despite cargo estimates
- **WHEN** 用户明确指定的车型已经匹配成功，且货物画像显示其他车型可能更合适
- **THEN** 系统仍保留用户匹配车型，不执行能力校验结论，也不自动替换车型

### Requirement: Estimate when no usable user vehicle exists

当用户未提供车型，或用户车型原文无法唯一匹配车型主数据时，系统 SHALL 根据当前完整货物画像及由有效城市目录提供的车型能力字段使用确定性计算估算车型，结果来源标记为 `estimated`，并最多返回三个通过计算的候选车型；不得调用 LLM 选择车型。有效城市优先取订单起点城市，缺失时取调用方提供的用户定位城市。

#### Scenario: Estimate without a vehicle expression
- **WHEN** 用户只输入货物、重量或数量等订单信息，未提供车型
- **THEN** 系统读取货物画像和车型主数据，通过重量、体积和简化极点装载计算返回最多三个车型候选，来源为 `estimated`

#### Scenario: Fall back from an ambiguous expression
- **WHEN** 用户输入“大车”“小车”“之前那辆车”或其他无法唯一匹配的车型表达
- **THEN** 系统不强制映射该表达，使用确定性计算估算最多三个车型，并保留原始表达作为决策原因

#### Scenario: Estimate with pickup city catalog
- **WHEN** 用户未提供车型且订单起点城市为温州
- **THEN** 系统使用温州目录进行重量、体积和极点装载计算

#### Scenario: Fall back to user location
- **WHEN** 订单起点城市缺失但用户定位城市为上海
- **THEN** 系统使用上海目录进行车型估算

#### Scenario: Fall back to global data
- **WHEN** 起点城市和用户定位城市均缺失，或城市没有覆盖数据
- **THEN** 系统使用全国默认目录完成车型估算

### Requirement: Preserve unresolved vehicle input

无法匹配的车型原文 SHALL 保留在决策结果或诊断信息中，但不得写入 `OrderContext.vehicle_type` 或 `vehicle_specs` 作为 canonical 值；已有 canonical 车型上下文不得因本次未匹配输入被覆盖。

#### Scenario: Do not overwrite context with an unresolved vehicle
- **WHEN** 当前上下文已有 `truck_5m2`，本轮输入“换成大车”且“大车”无法唯一匹配
- **THEN** 系统保留当前 canonical 车型，并以该轮货物画像生成估算结果或待处理结果，不将“大车”写入车型字段

### Requirement: Return an explainable resolution result

车型决策结果 SHALL 至少包含最终车型、车型特殊规格（如有）、来源和原因；估算结果还 SHALL 包含 0 至 3 个通过确定性计算的候选车型，并记录 `effective_city`、`vehicle_data_source`、目录版本及是否使用过期缓存。来源 SHALL 为 `user_matched` 或 `estimated`。本能力 SHALL 不输出 `feasible`、`infeasible` 或其他能力校验结论。

#### Scenario: Report user match source
- **WHEN** 用户车型成功匹配主数据
- **THEN** 结果包含 canonical 车型及 `source="user_matched"`

#### Scenario: Report estimation source
- **WHEN** 车型由货物画像推断得到
- **THEN** 结果包含估算车型及 `source="estimated"`，原因说明估算依据

#### Scenario: Report catalog provenance
- **WHEN** 车型由城市目录估算得到
- **THEN** 结果包含有效城市、目录来源和目录版本
