# conversation-order-context Specification

## Purpose

为多轮订单识别提供可持久化的会话历史、当前订单草稿状态和可测试的实体 action 合并能力，并支持解析结果在后续订单流程中稳定复用。
## Requirements
### Requirement: Conversation history

系统 SHALL 提供会话历史，保存有序的 user、assistant 和 system 对话回合，并支持获取最近回合、转换为 LLM 消息格式和稳定序列化。CLI 处理成功后写入的 assistant 回合 SHALL 是精简摘要，不包含完整调试输出。

#### Scenario: Append and retrieve turns

- **WHEN** 会话追加 user 与 assistant 回合并请求最近记录
- **THEN** 系统按追加顺序返回对应 turns，并保留 role、content 和时间信息

#### Scenario: Format history for LLM

- **WHEN** 调用会话历史的 LLM 格式化方法
- **THEN** 系统返回包含 role/content 的消息序列，不修改原始内容

#### Scenario: Store concise assistant summary

- **WHEN** 一轮普通消息成功完成处理
- **THEN** history 追加一条 assistant 回合，内容只概括最终主意图、订单处理/澄清状态、实体数量和上下文更新状态等必要信息

#### Scenario: Do not store debug payloads

- **WHEN** assistant 摘要写入 history
- **THEN** 摘要不包含完整实体 JSON、完整 OrderContext、原始 LLM content、提示词或错误堆栈

#### Scenario: Failed processing does not append assistant

- **WHEN** graph 或 reducer 处理失败
- **THEN** history 不追加本轮 assistant 摘要

### Requirement: Active order context

系统 SHALL 提供单一 active 订单上下文，覆盖 pickup/dropoff、联系人、货物、车型、时间、支付、发票、服务和备注等订单字段，并支持稳定序列化。

#### Scenario: Empty context
- **WHEN** 创建新的订单上下文
- **THEN** 所有可选单值字段为空、集合字段为空，且可序列化为 JSON-compatible 字典

#### Scenario: Session combines history and order
- **WHEN** 创建一个会话
- **THEN** 会话同时持有历史对话和 active 订单上下文，二者可独立更新

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

### Requirement: No business side effects

上下文和实体合并 SHALL 只进行内存状态转换，不查询历史订单、不写入数据库、不创建或确认订单。

#### Scenario: Reduction is pure in-memory

- **WHEN** 对订单实体列表执行合并
- **THEN** 系统只返回上下文数据，不触发外部订单或数据库调用
