## MODIFIED Requirements

### Requirement: Rewrite before extraction

系统 SHALL 先使用当前消息、历史对话和订单上下文生成 rewrite 结果，再将 rewrite 结果中的 `extraction_text` 提供给 grounded entity extraction 阶段。

#### Scenario: Extract incremental request after rewrite

- **WHEN** 当前订单已有一吨苹果，用户输入“再加一吨苹果”
- **THEN** 子图保留 rewrite 的增量动作语义，并将对应 `extraction_text` 用于提取带 attributes.action=`add` 的 cargo entity

#### Scenario: Extraction uses rewritten extraction text

- **WHEN** rewrite 成功返回 `extraction_text`
- **THEN** extract 阶段使用该文本并返回可定位的实体结果，而不是再次基于原始消息独立推理上下文

### Requirement: Keep parsing-only boundary

订单处理子图 SHALL 只负责 rewrite、grounded entity extraction、澄清路由和内存订单上下文更新；不得调用历史订单服务、订单创建或确认工具，不得写入数据库。

#### Scenario: Parsing uses mapped grounded entities

- **WHEN** 提取阶段返回带 attributes.action 的 grounded 订单实体
- **THEN** 子图将 LLM 决策的 attributes 原样应用到当前 OrderContext 并返回新上下文，不触发外部业务副作用
