## MODIFIED Requirements

### Requirement: Rewrite before extraction

系统 SHALL 先使用当前消息、历史对话和订单上下文生成 rewrite 结果，再将 rewrite 结果中的 `extraction_text` 与 reference time 提供给 grounded entity extraction 阶段。实体提取阶段不得再次基于原始消息、历史对话或订单上下文独立推理业务语义。

#### Scenario: Extract incremental request after rewrite

- **WHEN** 当前订单已有一吨苹果，用户输入“再加一吨苹果”
- **THEN** rewrite 输出保留增量语义的 extraction text，提取阶段输出 attributes.action=`add` 的 cargo entity

#### Scenario: Extraction uses rewritten extraction text

- **WHEN** rewrite 成功返回 `extraction_text`
- **THEN** extract 阶段仅使用该文本与 reference time 返回可定位实体，而不是再次读取原始消息、历史或订单上下文
