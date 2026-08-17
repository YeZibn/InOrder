## MODIFIED Requirements

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

### Requirement: No business side effects

上下文和实体合并 SHALL 只进行内存状态转换，不查询历史订单、不写入数据库、不创建或确认订单。

#### Scenario: Reduction is pure in-memory

- **WHEN** 对订单实体列表执行合并
- **THEN** 系统只返回上下文数据，不触发外部订单或数据库调用

