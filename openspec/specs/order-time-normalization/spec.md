# order-time-normalization Specification

## Purpose

为订单和历史查询提供可验证、可分类且带明确用途的时间实体，避免下游直接依赖未经校验的 LLM 时间输出。

## Requirements

### Requirement: Validate time boundaries

系统 SHALL 校验时间实体的 `start`、`end` 和 `context`，统一为带 `Asia/Shanghai` 时区的标准时间表示。

#### Scenario: Validate closed interval

- **WHEN** 输入合法且 `start` 早于 `end` 的时间边界
- **THEN** 系统返回带时区的规范化 start/end，并保留 context

#### Scenario: Validate open interval

- **WHEN** 输入仅有 start 或仅有 end 的合法开区间
- **THEN** 系统接受该时间实体，并将缺失边界保持为空

#### Scenario: Reject invalid boundaries

- **WHEN** start 和 end 均为空、格式非法或 start 晚于 end
- **THEN** 系统返回明确的时间归一化错误

### Requirement: Classify fixed time and range

系统 SHALL 根据归一化后的边界将时间实体分类为 `fixed` 或 `range`，并保留 start/end 字段。

#### Scenario: Classify fixed time

- **WHEN** start 与 end 同时存在且相等
- **THEN** 系统返回 `kind=fixed`

#### Scenario: Classify time range

- **WHEN** start/end 不相等，或时间实体为单边开区间
- **THEN** 系统返回 `kind=range`

### Requirement: Preserve raw expression

归一化结果 SHALL 保留用户原始时间表达，以支持展示、审计和错误诊断。

#### Scenario: Preserve raw time

- **WHEN** 将“明天下午三点”归一化为固定时间
- **THEN** 结果同时保留原始表达和规范化边界

### Requirement: Separate order and history time contexts

系统 SHALL 保留并校验 `context` 为 `new_order` 或 `history`，并确保 history 时间不会直接写入当前订单的 `delivery_time`。

#### Scenario: Route new order time

- **WHEN** 时间 context 为 `new_order`
- **THEN** 该时间可作为当前订单配送时间处理

#### Scenario: Keep history time out of delivery context

- **WHEN** 时间 context 为 `history`
- **THEN** 该时间仅作为历史查询条件，不覆盖当前订单配送时间

### Requirement: Pure time normalization

时间归一化 SHALL 只返回新的规范化实体，不修改输入实体、会话历史或订单上下文，也不调用外部服务。

#### Scenario: Normalize without side effects

- **WHEN** 对时间实体执行归一化
- **THEN** 输入实体和订单上下文保持不变
