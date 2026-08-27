# llm-streaming Specification

## Purpose

为本地 CLI 和上层调用方提供可观察、可测试且兼容两种 OpenAI-compatible 接口的实时 LLM 增量输出能力，同时保留结构化业务链路所需的完整响应。

## Requirements

### Requirement: Stream normalized content across providers
系统 SHALL 为 Chat Completions 和 Responses 两种 API 提供统一的增量文本事件语义，调用方无需根据 API 模式解析供应商事件格式。系统 SHALL 将 OpenAI 和 DeepSeek 在 Chat Completions 或 Responses 模式下返回的流式事件归一化为统一的增量文本和完成事件；provider 差异不得泄露给上层工作流。

#### Scenario: Chat Completions delta
- **WHEN** Chat Completions 返回包含 `choices[0].delta.content` 的 SSE 事件
- **THEN** 系统将该内容作为增量文本事件交给调用方

#### Scenario: Responses delta
- **WHEN** Responses 返回 `response.output_text.delta` 事件
- **THEN** 系统将其 `delta` 内容作为同一种增量文本事件交给调用方

#### Scenario: Stream DeepSeek Chat Completions

- **WHEN** DeepSeek Chat Completions 返回多个 SSE content chunks 并以 `[DONE]` 结束
- **THEN** 客户端按顺序累积 content，产生统一完成结果和可选 usage

#### Scenario: Stream DeepSeek Responses

- **WHEN** DeepSeek Responses 返回 `response.output_text.delta` 及最终 `response.completed`/`response.incomplete`/`response.failed`
- **THEN** 客户端按顺序累积 delta，并将最终状态归一化为统一结果或结构化错误

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

### Requirement: Streaming lifecycle and errors
系统 SHALL 将认证、无效请求、超时、限流及上游错误归一化为现有 LLM 错误类型，并按照增量交付边界处理重试。

#### Scenario: Provider failure before content
- **WHEN** 首个文本增量到达前发生可重试的上游错误
- **THEN** 系统按现有重试策略重新发起请求，且不向调用方交付不完整结果

#### Scenario: Provider failure after content
- **WHEN** 已交付至少一个文本增量后发生连接或上游错误
- **THEN** 系统终止本次流并抛出归一化错误，不自动重试并拼接重复响应

### Requirement: Structured response prefix tolerance
结构化 JSON 解析 SHALL 容忍响应文本开头的 UTF-8 BOM 和零宽格式字符；清洗范围 SHALL 限于文本开头，不得修改正文内容。

#### Scenario: Invisible prefix before JSON
- **WHEN** 完整流式响应以 BOM 或零宽格式字符开头，后面紧跟合法 JSON
- **THEN** 系统清理这些开头字符并成功解析 JSON

#### Scenario: Invisible character inside JSON string
- **WHEN** 不可见字符出现在 JSON 字符串值内部
- **THEN** 系统保留该字符，不执行全文清洗或改变字符串语义
