# order-rewrite Specification

## Purpose

为多轮订单输入提供保留动作语义的上下文重写能力，使省略、指代和增量表达能够被后续实体提取器稳定处理。

## Requirements

### Requirement: Context-aware incremental rewrite

系统 SHALL 接收用户本轮输入、会话历史和当前订单上下文，并输出可供实体提取器处理的增量语义文本。

#### Scenario: Rewrite incremental cargo request
- **WHEN** 当前订单已有一吨香蕉，用户输入“再加一吨苹果”
- **THEN** 系统输出包含当前事实和新增动作的重写结果，并将 extraction_text 表达为新增一吨苹果

#### Scenario: Rewrite scalar replacement
- **WHEN** 当前订单装货地为上海，用户输入“改到杭州”
- **THEN** 系统将本轮请求重写为替换装货地为杭州，不生成无关订单字段

### Requirement: Preserve entity action semantics

重写 SHALL 保留用户本轮操作的 set、add、remove、replace 语义，不得将增量、删除或替换表达改写成无动作的完整订单陈述。

#### Scenario: Preserve add action
- **WHEN** 用户输入“再加一吨苹果”
- **THEN** extraction_text 明确表达新增动作

#### Scenario: Preserve remove action
- **WHEN** 当前上下文存在苹果，用户输入“苹果不要了”
- **THEN** extraction_text 明确表达移除苹果

### Requirement: Best-effort ambiguity handling

系统 SHALL 只使用当前订单上下文和当前会话中明确的对话信息解决省略或指代；存在多个候选时 SHALL 选择最合理的解释，生成可执行的 extraction_text，不得以澄清状态阻断提取链路。系统不解析历史订单引用，也不从外部历史订单恢复字段。

#### Scenario: Ambiguous current-conversation reference
- **WHEN** 当前会话中存在多个车型候选，用户输入“换回刚才提到的车”
- **THEN** 系统基于当前订单上下文和会话消息生成非空 rewritten_text 和 extraction_text，无法确定时保留原文表达，不查询历史订单

#### Scenario: Missing context does not force clarification
- **WHEN** 当前上下文为空，用户输入“再加一吨苹果”
- **THEN** 系统将其保守重写为本轮新增一吨苹果，不虚构已有货物

### Requirement: Structured rewrite result

系统 SHALL 返回只包含 `rewritten_text` 和 `extraction_text` 的结构化结果；两个字段都必须是字符串。

#### Scenario: Successful structured result
- **WHEN** rewrite 成功且语义可确定
- **THEN** 系统返回非空 rewritten_text 和 extraction_text，不包含澄清字段

#### Scenario: Invalid model output
- **WHEN** LLM 返回非法 JSON、缺少必需字段或字段类型错误
- **THEN** 系统抛出结构化响应错误，不返回部分结果

### Requirement: Rewrite has no side effects

rewrite SHALL 只生成结果，不修改 HistoryConversation 或 OrderContext，不调用订单查询、数据库或订单业务工具。

#### Scenario: Input contexts remain unchanged
- **WHEN** 对包含历史和订单字段的请求执行 rewrite
- **THEN** 调用前后的两个上下文内容保持一致

