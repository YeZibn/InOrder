## MODIFIED Requirements

### Requirement: Load and validate client configuration

系统 SHALL 从运行时配置中读取模型服务的 API key、provider、base URL、模型标识和可选的 `LLM_API_MODE`；provider SHALL 为 `openai` 或 `deepseek`，接口模式 SHALL 为 `chat_completions` 或 `responses`。未配置 provider 时默认为 `openai`；缺少必需配置或配置值非法时 SHALL 拒绝发起请求并返回明确的配置错误。系统 SHALL 支持可选的 provider-compatible reasoning effort；DeepSeek V4 思考模式启用后 reasoning_effort 仅接受 `high`/`max`，且 `thinking` 参数与 `reasoning_content` 解析不在本变更范围。

#### Scenario: Load a valid DeepSeek configuration

- **WHEN** 配置包含 `LLM_PROVIDER=deepseek`、API key、base URL（或默认地址）和模型
- **THEN** 客户端成功加载配置并保留 provider、接口模式和模型信息

#### Scenario: Reject unsupported provider

- **WHEN** `LLM_PROVIDER` 不是 `openai` 或 `deepseek`
- **THEN** 配置加载失败并返回配置错误，不创建可调用客户端

#### Scenario: Preserve existing OpenAI defaults

- **WHEN** 未配置 `LLM_PROVIDER`
- **THEN** 客户端按 `openai` provider 和既有默认接口模式加载

### Requirement: Select an upstream API mode

系统 SHALL 根据 `LLM_API_MODE` 选择 Chat Completions 或 Responses API；未设置时使用 `chat_completions`。provider 不得覆盖调用方显式选择的 API mode。

#### Scenario: Use DeepSeek Chat Completions

- **WHEN** provider 为 `deepseek` 且 API mode 为 `chat_completions`
- **THEN** 客户端使用 DeepSeek 兼容的 messages 请求和 Chat Completions 响应归一化

#### Scenario: Use DeepSeek Responses

- **WHEN** provider 为 `deepseek` 且 API mode 为 `responses`
- **THEN** 客户端使用 DeepSeek Responses 的 input 请求和 output text 响应归一化
