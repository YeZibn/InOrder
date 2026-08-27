## MODIFIED Requirements

### Requirement: Best-effort ambiguity handling

系统 SHALL 只使用当前订单上下文和当前会话中明确的对话信息解决省略或指代；存在多个候选时 SHALL 选择最合理的解释，生成可执行的 extraction_text，不得以澄清状态阻断提取链路。系统不解析历史订单引用，也不从外部历史订单恢复字段。

#### Scenario: Ambiguous current-conversation reference
- **WHEN** 当前会话中存在多个车型候选，用户输入“换回刚才提到的车”
- **THEN** 系统基于当前订单上下文和会话消息生成非空 rewritten_text 和 extraction_text，无法确定时保留原文表达，不查询历史订单

#### Scenario: Missing context does not force clarification
- **WHEN** 当前上下文为空，用户输入“再加一吨苹果”
- **THEN** 系统将其保守重写为本轮新增一吨苹果，不虚构已有货物
