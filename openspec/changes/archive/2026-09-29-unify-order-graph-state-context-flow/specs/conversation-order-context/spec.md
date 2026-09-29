## ADDED Requirements

### Requirement: Persist only the successfully completed order context

会话 SHALL 将唯一的 `OrderContext` 快照作为跨轮订单业务状态。单次工作流中的输入快照、更新中快照、本轮实体和派生结果不得形成另一份跨轮订单状态。调用方 SHALL 仅在订单处理成功并返回最终上下文后，用该上下文替换会话当前值；失败时 SHALL 保留原有订单上下文。

#### Scenario: Commit the completed order snapshot
- **WHEN** 订单工作流成功返回更新后的 `OrderContext`
- **THEN** 会话将该快照作为唯一当前订单上下文供下一轮使用

#### Scenario: Preserve the prior snapshot on failure
- **WHEN** 订单工作流在最终结果返回前失败
- **THEN** 会话不保存图内的部分更新，原有 `OrderContext` 继续作为当前订单上下文

#### Scenario: Do not persist turn entities as order state
- **WHEN** 一轮工作流成功处理实体变更
- **THEN** 会话持久化合并后的 `OrderContext`，不把本轮实体列表另存为第二份订单状态

## MODIFIED Requirements

### Requirement: Entity action reduction

系统 SHALL 将已归一化订单实体中的 `set`、`add`、`remove` 和 `replace` action 应用到订单上下文，并返回更新后的上下文。调用 Reducer 前 SHALL 先对本轮实体执行统一归一化；Reducer SHALL 只应用实体中已归一化的字段值，不得再次执行时间、手机号、枚举、车型或车型规格归一化，也不得再次对车型或规格执行别名/模糊目录匹配。对于货物实体，系统 SHALL 按 `name` 聚合同类货物，并将 `weight`、`quantity`、`volume` 和 `dimensions` 保存为原始值列表；当前阶段不得进行单位换算或数值相加。

#### Scenario: Set and replace scalar field
- **WHEN** 对 pickup_location 执行 set，再对其执行 replace
- **THEN** 上下文只保留 replace 后的地址

#### Scenario: Add raw cargo increment
- **WHEN** 上下文已有某货物原始属性，应用同货物的已归一化 add entity
- **THEN** 本轮非空货物属性追加到对应列表，不覆盖旧值，也不进行数值合并

#### Scenario: Ignore null cargo attributes during add
- **WHEN** 已归一化 add entity 的某些货物属性为 null
- **THEN** null 属性被忽略，不能触发错误或写入 null 列表项

#### Scenario: Remove cargo
- **WHEN** 对已有货物应用已归一化 remove entity
- **THEN** 该货物从上下文中移除

#### Scenario: Replace list field
- **WHEN** 对 vehicle_specs 或 remark 应用已归一化 replace entity
- **THEN** 系统用新值替换该字段的旧值

#### Scenario: Apply canonical values from normalization
- **WHEN** Reducer 收到包含已归一化枚举、手机号或车型值的实体
- **THEN** Reducer 将这些字段值及其 action 应用到上下文，不再自行解释或改写这些字段值

#### Scenario: Require normalization before direct reduction
- **WHEN** 调用方直接调用实体 action Reducer
- **THEN** 调用方先执行统一实体归一化，Reducer 本身只负责应用 action
