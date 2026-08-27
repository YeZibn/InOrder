## MODIFIED Requirements

### Requirement: Complete streaming result
流式调用 SHALL 按接收顺序累积所有**内容增量**（content delta），并在正常结束后返回与非流式调用兼容的完整 `LLMResponse`；非内容事件（含 `response.reasoning_text.delta` 等推理增量）SHALL 不得进入最终文本，也不得通过增量回调交付给调用方。

#### Scenario: Normal completion
- **WHEN** 流式响应正常结束
- **THEN** 调用方收到完整文本，且文本等于所有内容增量按顺序拼接的结果

#### Scenario: Reasoning deltas excluded from result
- **WHEN** Responses 流式响应包含 `response.reasoning_text.delta` 事件，其后跟随 `response.output_text.delta` 事件
- **THEN** 最终文本仅包含 `output_text.delta` 的拼接结果，reasoning 增量不出现在最终文本中

#### Scenario: Reasoning deltas not delivered to callback
- **WHEN** Responses 流式响应包含推理增量事件且调用方注册了增量回调
- **THEN** 回调仅收到内容增量，不收到推理增量

#### Scenario: Retry marker reflects content only
- **WHEN** 仅收到推理增量后发生可重试的上游错误
- **THEN** 系统按未交付内容处理（允许重试）；仅内容增量已交付后才视为不可重试

#### Scenario: Empty content events
- **WHEN** 流中包含角色、结束标记或无文本事件
- **THEN** 系统忽略非文本内容对最终文本的影响，但正确识别完成状态
