## MODIFIED Requirements

### Requirement: Active order context

系统 SHALL 提供单一 active 订单上下文，覆盖 pickup/dropoff、联系人、货物、车型、时间、支付、发票、服务和备注等订单字段，并支持稳定序列化。订单上下文 SHALL 在保留原始 `cargo` 列表的同时，可选保存基于完整货物集合生成的 `cargo_profiles` 和 `cargo_profile_summary` 派生字段，并保存本会话稳定复用的 `reference_time` 时间锚点。

#### Scenario: Empty context

- **WHEN** 创建新的订单上下文
- **THEN** 所有可选单值字段为空、集合字段为空，货物画像及其汇总为空或未生成，`reference_time` 为空，且上下文可序列化为 JSON-compatible 字典

#### Scenario: Persist reference time in context

- **WHEN** 一轮请求确定了有效的 `reference_time`
- **THEN** 更新后的 `OrderContext` 保存该值，并在序列化快照中以 `YYYY-MM-DD HH:MM` 格式返回

#### Scenario: Reuse persisted reference time

- **WHEN** 后续请求携带已有 `OrderContext.reference_time`
- **THEN** 系统优先使用上下文中的值作为时间锚点，不以本机当前时间或后续请求传入的不同值覆盖

#### Scenario: Clear persisted reference time

- **WHEN** 用户清空会话或创建新的订单上下文
- **THEN** `reference_time` 被清除，下一轮请求可以重新确定时间锚点

#### Scenario: Session combines history and order

- **WHEN** 创建一个会话
- **THEN** 会话同时持有历史对话和 active 订单上下文，二者可独立更新

#### Scenario: Preserve raw cargo beside profile

- **WHEN** 订单上下文已包含原始货物和对应画像
- **THEN** 原始 `cargo` 表达保持不变，画像作为独立派生数据序列化

#### Scenario: Replace profile after cargo mutation

- **WHEN** 原始货物发生新增、替换或删除并重新生成画像
- **THEN** `cargo_profiles` 和 `cargo_profile_summary` 整体替换，不与旧画像增量拼接
