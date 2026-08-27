## MODIFIED Requirements

### Requirement: Keep parsing-only boundary

订单处理子图 SHALL 只负责 rewrite、grounded 实体提取、订单上下文更新、货物画像和确定性车型解析/估算，以及基于当前订单上下文的完整性检查和摘要；不得查询历史订单、读取外部历史订单数据、执行订单创建或确认，不得写入数据库。用户车型匹配成功时不得因货物画像而替换车型。对于提取结果中的业务 attributes，子图 SHALL 原样应用 LLM 已作出的 action 和字段决策，不得自行补全或重判。

#### Scenario: Parsing applies mapped grounded entities in memory only
- **WHEN** 子图提取出带 action 的当前订单实体
- **THEN** 子图将实体的 LLM 决策 attributes 原样应用到当前 `OrderContext` 并返回新上下文，不触发外部业务副作用

#### Scenario: Structured failures do not update context
- **WHEN** rewrite 或 extract 因结构化输出错误导致子图失败
- **THEN** 子图不返回部分更新后的上下文

#### Scenario: Vehicle resolution has no external side effect
- **WHEN** 子图执行车型解析或估算
- **THEN** 结果只更新内存中的订单状态和派生决策，不触发外部业务副作用

#### Scenario: Completeness check has no external side effect
- **WHEN** 子图执行当前订单完整性检查和摘要生成
- **THEN** 系统只读取当前订单上下文并返回摘要，不查询历史订单、不创建订单、不写入数据库且不调用外部服务
