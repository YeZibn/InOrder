## MODIFIED Requirements

### Requirement: Keep profile generation separate from vehicle selection

货物画像生成 SHALL 继续只输出货物属性和汇总约束，不直接选择车型；车型解析/估算阶段可以读取当前完整货物画像及汇总结果，但不得要求货物画像阶段输出车型字段。

#### Scenario: Profile remains vehicle-agnostic
- **WHEN** 系统完成货物画像
- **THEN** 画像输出不包含 `vehicle_type`、`vehicle_specs`、`recommended_vehicle` 或能力校验结论，车型估算在后续阶段读取画像
