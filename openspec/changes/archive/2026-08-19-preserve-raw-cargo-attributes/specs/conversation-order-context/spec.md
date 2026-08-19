## MODIFIED Requirements

### Requirement: Entity action reduction

系统 SHALL 将订单实体的 `set`、`add`、`remove` 和 `replace` action 应用到订单上下文，并返回更新后的上下文。对于货物实体，系统 SHALL 按 `name` 聚合同类货物，并将 `weight`、`quantity`、`volume` 和 `dimensions` 保存为原始值列表；当前阶段不得进行单位换算或数值相加。

#### Scenario: Set and replace scalar field

- **WHEN** 对 pickup_location 执行 set，再对其执行 replace
- **THEN** 上下文只保留 replace 后的地址

#### Scenario: Add raw cargo increment

- **WHEN** 上下文已有某货物原始属性，应用同货物的 add entity
- **THEN** 本轮非空货物属性追加到对应列表，不覆盖旧值，也不进行数值合并

#### Scenario: Ignore null cargo attributes during add

- **WHEN** add entity 的某些货物属性为 null
- **THEN** null 属性被忽略，不能触发错误或写入 null 列表项

#### Scenario: Remove cargo

- **WHEN** 对已有货物应用 remove entity
- **THEN** 该货物从上下文中移除

#### Scenario: Replace list field

- **WHEN** 对 vehicle_specs 或 remark 应用 replace entity
- **THEN** 系统用新值替换该字段的旧值

