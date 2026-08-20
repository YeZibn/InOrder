## MODIFIED Requirements

### Requirement: Rewrite incremental order semantics

系统 SHALL 根据当前用户输入、`HistoryConversation` 和 `OrderContext` 生成可供实体提取器处理的 `rewritten_text` 与 `extraction_text`。rewrite SHALL 保留本轮动作和增量语义；当指代存在多个合理候选时，仍 SHALL 选择基于当前上下文最合理的解释并生成可执行的 extraction_text，不得以澄清状态阻断提取链路。

#### Scenario: Rewrite ambiguous reference with best-effort context

- **WHEN** 用户输入包含指代且历史或订单上下文存在多个候选对象
- **THEN** 系统 SHALL 根据当前订单上下文和最近对话选择最合理候选，返回非空 `rewritten_text` 和 `extraction_text`，并继续进入实体提取

#### Scenario: Rewrite output contains only executable text

- **WHEN** rewrite 成功
- **THEN** 输出 SHALL 只包含 `rewritten_text` 和 `extraction_text` 两个字符串字段，不包含 `needs_clarification` 或 `clarification_reason`
