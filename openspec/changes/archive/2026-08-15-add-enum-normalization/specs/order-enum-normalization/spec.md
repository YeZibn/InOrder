## Purpose

为订单实体提供稳定、可校验且可重复执行的枚举归一化行为，使自然语言表达能够安全地写入订单上下文。

## ADDED Requirements

### Requirement: Normalize supported order enums

系统 SHALL 将支付方式、发票类型、本人跟车标记和服务类型的中文表达及已支持别名转换为稳定的内部值。

#### Scenario: Normalize payment type

- **WHEN** 输入“到付、货到付款或运费到付”
- **THEN** 系统返回 `payment_type=0`
- **WHEN** 输入“预付、提前付款或先付款”
- **THEN** 系统返回 `payment_type=1`

#### Scenario: Normalize invoice type

- **WHEN** 输入“不开票、普票或电子普票”
- **THEN** 系统返回 `invoice_type=1`
- **WHEN** 输入“专票或纸质专票”
- **THEN** 系统返回 `invoice_type=2`

#### Scenario: Normalize follow flag

- **WHEN** 输入“本人跟车或我跟车”
- **THEN** 系统返回 `oneself_follow_flag=1`
- **WHEN** 输入“非本人跟车或他人跟车”
- **THEN** 系统返回 `oneself_follow_flag=2`

#### Scenario: Normalize service type

- **WHEN** 输入快车、特快、用户出价或拼车及其支持的别名
- **THEN** 系统分别返回 `express`、`urgent`、`user_bid` 或 `shared`

### Requirement: Idempotent normalization

系统 SHALL 接受原始中文表达、已归一化数值和已归一化服务 code，并保证重复归一化不会改变结果。

#### Scenario: Normalize already normalized values

- **WHEN** 对 `payment_type=1` 或 `service_type=express` 再次执行归一化
- **THEN** 系统返回相同的内部值且不产生新的转换

### Requirement: Reject unknown enum values

系统 SHALL 对无法映射到受支持枚举的值返回明确的归一化错误或未知状态，不得静默猜测为其他枚举。

#### Scenario: Unknown payment method

- **WHEN** 输入当前未支持的“月结”支付方式
- **THEN** 系统报告未知枚举，并保留原始表达供上层澄清

### Requirement: Preserve raw enum expression

归一化结果 SHALL 能够保留用户原始枚举表达，以支持展示、审计和错误诊断。

#### Scenario: Preserve raw value

- **WHEN** 将“提前付款”归一化为预付
- **THEN** 结果同时保留原始表达“提前付款”和内部值 `1`

### Requirement: Normalizer has no side effects

枚举归一化 SHALL 只转换输入实体，不修改会话历史、订单上下文或调用外部服务。

#### Scenario: Pure normalization

- **WHEN** 对包含枚举实体的输入执行归一化
- **THEN** 原始实体和订单上下文保持不变，只返回归一化结果
