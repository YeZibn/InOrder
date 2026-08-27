## MODIFIED Requirements

### Requirement: Route requests by provider and API mode

系统 SHALL 使用配置的 provider、base URL、模型和 API key，根据 `LLM_API_MODE` 通过 `chat.completions.create` 或 `responses.create` 发送请求；默认 provider 为 `openai`，默认 API mode 为 `chat_completions`。`LLM_BASE_URL` 只表示服务根路径。

#### Scenario: DeepSeek Chat Completions request

- **WHEN** `LLM_PROVIDER=deepseek` 且 `LLM_API_MODE=chat_completions`
- **THEN** 请求发送到 DeepSeek 服务根地址下的 `/chat/completions`，消息使用 `messages` 字段，响应按 Chat Completions 结构解析

#### Scenario: DeepSeek Responses request

- **WHEN** `LLM_PROVIDER=deepseek` 且 `LLM_API_MODE=responses`
- **THEN** 请求发送到 DeepSeek 服务根地址下的 `/responses`，输入使用 `input` 字段，响应按 Responses output text 结构解析

#### Scenario: Provider-specific reasoning parameters

- **WHEN** 调用方配置 reasoning effort 且目标 provider/API mode 支持该参数
- **THEN** transport 使用目标接口要求的参数结构；不支持的 provider 参数不得发送
- **AND** DeepSeek V4 思考模式下 reasoning_effort 仅接受 `high`/`max`；V4 思考模式需通过 `thinking` 参数单独启用，不在本变更 transport 范围内
