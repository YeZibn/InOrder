## MODIFIED Requirements

### Requirement: Stream normalized content across providers

系统 SHALL 将 OpenAI 和 DeepSeek 在 Chat Completions 或 Responses 模式下返回的流式事件归一化为统一的增量文本和完成事件；provider 差异不得泄露给上层工作流。

#### Scenario: Stream DeepSeek Chat Completions

- **WHEN** DeepSeek Chat Completions 返回多个 SSE content chunks 并以 `[DONE]` 结束
- **THEN** 客户端按顺序累积 content，产生统一完成结果和可选 usage

#### Scenario: Stream DeepSeek Responses

- **WHEN** DeepSeek Responses 返回 `response.output_text.delta` 及最终 `response.completed`/`response.incomplete`/`response.failed`
- **THEN** 客户端按顺序累积 delta，并将最终状态归一化为统一结果或结构化错误
