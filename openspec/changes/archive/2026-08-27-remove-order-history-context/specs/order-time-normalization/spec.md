## MODIFIED Requirements

### Requirement: Validate time boundaries

系统 SHALL 校验时间实体的 `start` 和 `end`，统一为带 `Asia/Shanghai` 时区的标准时间表示；时间实体不包含业务上下文分流字段。

#### Scenario: Validate closed interval

- **WHEN** 输入合法且 `start` 早于 `end` 的时间边界
- **THEN** 系统返回带时区的规范化 start/end，不生成或要求 `new_order/history` 字段

#### Scenario: Validate open interval

- **WHEN** 输入仅有 start 或仅有 end 的合法开区间
- **THEN** 系统接受该时间实体，并将缺失边界保持为空

#### Scenario: Reject invalid boundaries

- **WHEN** start 和 end 均为空、格式非法或 start 晚于 end
- **THEN** 系统返回明确的时间归一化错误

## REMOVED Requirements

### Requirement: Separate order and history time contexts

**Reason**：当前系统只处理当前订单，不实现历史订单查询或历史订单时间条件。

**Migration**：所有送达时间统一使用同一时间实体结构，仅通过 start/end 表示边界。
