## MODIFIED Requirements

### Requirement: Estimate when no usable user vehicle exists

当用户未提供车型，或用户车型原文无法唯一匹配车型主数据时，系统 SHALL 根据当前完整货物画像及由有效城市目录提供的车型能力字段使用确定性计算估算车型，结果来源标记为 `estimated`，并最多返回三个通过计算的候选车型；不得调用 LLM 选择车型。有效城市优先取订单起点城市，缺失时取调用方提供的用户定位城市。

#### Scenario: Estimate with pickup city catalog
- **WHEN** 用户未提供车型且订单起点城市为温州
- **THEN** 系统使用温州目录进行重量、体积和极点装载计算

#### Scenario: Fall back to user location
- **WHEN** 订单起点城市缺失但用户定位城市为上海
- **THEN** 系统使用上海目录进行车型估算

#### Scenario: Fall back to global data
- **WHEN** 起点城市和用户定位城市均缺失，或城市没有覆盖数据
- **THEN** 系统使用全国默认目录完成车型估算

### Requirement: Return an explainable resolution result

车型决策结果 SHALL 至少包含最终车型、车型特殊规格、来源和原因；估算结果还 SHALL 包含 0 至 3 个候选车型，并记录 `effective_city`、`vehicle_data_source`、目录版本及是否使用过期缓存。来源 SHALL 为 `user_matched` 或 `estimated`，本能力 SHALL 不输出能力校验结论。

#### Scenario: Report catalog provenance
- **WHEN** 车型由城市目录估算得到
- **THEN** 结果包含有效城市、目录来源和目录版本
