# conversation-order-context Specification

## Purpose

为多轮订单识别提供会话历史、当前订单草稿状态和可测试的实体 action 合并能力。

## Requirements

### Requirement: Conversation history

系统 SHALL 提供会话历史，保存有序的 user、assistant 和 system 对话回合，并支持获取最近回合和转换为 LLM 消息格式。

#### Scenario: Append and retrieve turns
- **WHEN** 会话追加 user 与 assistant 回合并请求最近记录
- **THEN** 系统按追加顺序返回对应 turns，并保留 role、content 和时间信息

#### Scenario: Format history for LLM
- **WHEN** 调用会话历史的 LLM 格式化方法
- **THEN** 系统返回包含 role/content 的消息序列，不修改原始内容

### Requirement: Active order context

系统 SHALL 提供单一 active 订单上下文，覆盖 pickup/dropoff、联系人、货物、车型、时间、支付、发票、服务和备注等订单字段，并支持稳定序列化。

#### Scenario: Empty context
- **WHEN** 创建新的订单上下文
- **THEN** 所有可选单值字段为空、集合字段为空，且可序列化为 JSON-compatible 字典

#### Scenario: Session combines history and order
- **WHEN** 创建一个会话
- **THEN** 会话同时持有历史对话和 active 订单上下文，二者可独立更新

### Requirement: Entity action reduction

系统 SHALL 将订单实体的 `set`、`add`、`remove` 和 `replace` action 应用到订单上下文，并返回更新后的上下文。

#### Scenario: Set and replace scalar field
- **WHEN** 对 pickup_location 执行 set，再对其执行 replace
- **THEN** 上下文只保留 replace 后的地址

#### Scenario: Add cargo increment
- **WHEN** 上下文已有某货物数量，应用同货物的 add entity
- **THEN** 系统累加数量或重量，不覆盖已有货物

#### Scenario: Remove cargo
- **WHEN** 对已有货物应用 remove entity
- **THEN** 该货物从上下文中移除

#### Scenario: Replace list field
- **WHEN** 对 vehicle_specs 或 remark 应用 replace entity
- **THEN** 系统用新值替换该字段的旧值

### Requirement: No business side effects

上下文和实体合并 SHALL 只进行内存状态转换，不查询历史订单、不写入数据库、不创建或确认订单。

#### Scenario: Reduction is pure in-memory
- **WHEN** 对订单实体列表执行合并
- **THEN** 系统只返回上下文数据，不触发外部订单或数据库调用
