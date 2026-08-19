## MODIFIED Requirements

### Requirement: Active order context

系统 SHALL 提供单一 active 订单上下文，覆盖 pickup/dropoff、联系人、货物、车型、时间、支付、发票、服务和备注等订单字段，并支持稳定序列化。订单上下文 SHALL 在保留原始 `cargo` 列表的同时，可选保存基于完整货物集合生成的 `cargo_profiles` 和 `cargo_profile_summary` 派生字段。

#### Scenario: Empty context

- **WHEN** 创建新的订单上下文
- **THEN** 所有可选单值字段为空、集合字段为空，货物画像及其汇总为空或未生成，且上下文可序列化为 JSON-compatible 字典

#### Scenario: Session combines history and order

- **WHEN** 创建一个会话
- **THEN** 会话同时持有历史对话和 active 订单上下文，二者可独立更新

#### Scenario: Preserve raw cargo beside profile

- **WHEN** 订单上下文已包含原始货物和对应画像
- **THEN** 原始 `cargo` 表达保持不变，画像作为独立派生数据序列化

#### Scenario: Replace profile after cargo mutation

- **WHEN** 原始货物发生新增、替换或删除并重新生成画像
- **THEN** `cargo_profiles` 和 `cargo_profile_summary` 整体替换，不与旧画像增量拼接
