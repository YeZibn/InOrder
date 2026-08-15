# order-phone-normalization Specification

## Purpose

为订单联系人手机号提供确定性、可校验且可追溯的归一化行为，将不同书写格式转换为稳定的内部号码，避免未经校验的文本直接进入订单上下文。

## Requirements

### Requirement: Normalize mainland mobile numbers

系统 SHALL 清理中国大陆手机号的常见格式字符，接受可选的 `+86` 或 `0086` 前缀，并将结果规范为 11 位手机号写入 `value`。归一化层 SHALL 优先读取 `attributes.value`，缺失时回退到 phone entity 的 `extraction_text`，不要求 extract LLM 预先完成格式转换。

#### Scenario: Normalize formatted number

- **WHEN** 输入 `138 0013 8000`、`138-0013-8000` 或带 `+86`/`0086` 前缀的号码
- **THEN** 系统返回 `value=13800138000`

#### Scenario: Preserve raw number

- **WHEN** 手机号被归一化
- **THEN** 结果保留用户原始表达 `raw`

### Requirement: Validate normalized number

系统 SHALL 校验归一化结果符合中国大陆手机号格式 `1[3-9]xxxxxxxxx`，不自动补位、截断或猜测错误号码。

#### Scenario: Reject invalid number

- **WHEN** 输入号码缺位、多位、首号段非法或包含无法清理的字符
- **THEN** 系统返回明确的手机号归一化错误

### Requirement: Preserve phone role and action semantics

手机号归一化 SHALL 保留 `sender`/`receiver` role 与原有 action；`set`、`replace` 和 `remove` 可继续作用于联系人手机号，`add` SHALL 被拒绝。

#### Scenario: Normalize sender phone

- **WHEN** 对 role 为 sender 的手机号执行 set 或 replace
- **THEN** 归一化后的 value 写入 sender_phone

#### Scenario: Reject phone add

- **WHEN** 对手机号实体执行 add
- **THEN** 系统返回不支持标量手机号增量的错误

### Requirement: Pure phone normalization

手机号归一化 SHALL 只返回新的归一化实体，不修改输入实体、会话历史或订单上下文，也不调用外部号码服务。

#### Scenario: Normalize without side effects

- **WHEN** 对手机号实体执行归一化
- **THEN** 输入实体保持不变
