## Purpose

让 InOrder 能通过统一配置在 OpenAI 与 DeepSeek 官方兼容服务之间切换，并为不同接口模式提供可校验的默认连接信息。

## ADDED Requirements

### Requirement: Select an LLM provider by configuration

系统 SHALL 提供 `LLM_PROVIDER` 配置，允许值为 `openai` 或 `deepseek`；未配置时 SHALL 使用 `openai`。非法 provider 值 SHALL 在发起上游请求前返回明确配置错误。

#### Scenario: Select DeepSeek official service

- **WHEN** `LLM_PROVIDER=deepseek` 且配置有效 API key 和模型
- **THEN** 系统使用 DeepSeek provider 配置创建 LLM 客户端，不需要修改业务工作流代码

#### Scenario: Reject an unknown provider

- **WHEN** `LLM_PROVIDER` 设置为不支持的值
- **THEN** 系统拒绝启动或请求，并返回 provider 配置错误

### Requirement: Resolve provider base URL safely

系统 SHALL 为 OpenAI 和 DeepSeek 提供官方服务根地址默认值，并允许显式 `LLM_BASE_URL` 覆盖默认值。`LLM_BASE_URL` SHALL 表示服务根路径，不包含具体 `/chat/completions` 或 `/responses` endpoint。

#### Scenario: Use DeepSeek default endpoint root

- **WHEN** provider 为 `deepseek` 且未设置 `LLM_BASE_URL`
- **THEN** 系统使用 `https://api.deepseek.com` 作为服务根地址，并由 API 模式选择具体 endpoint

#### Scenario: Override endpoint root for a compatible gateway

- **WHEN** 调用方显式设置 `LLM_BASE_URL`
- **THEN** 系统使用该地址连接对应 provider-compatible 服务，不重复拼接完整 endpoint

### Requirement: Resolve provider-specific API credentials

系统 SHALL 支持按 provider 独立配置 API Key，环境变量为 `LLM_API_KEY_OPENAI` 和 `LLM_API_KEY_DEEPSEEK`；解析优先级为 `LLM_API_KEY_<PROVIDER>` > `LLM_API_KEY`。所有 provider-specific key 与 fallback key 均未配置时 SHALL 在发起请求前返回明确配置错误。

#### Scenario: Use provider-specific key

- **WHEN** `LLM_PROVIDER=deepseek` 且配置了 `LLM_API_KEY_DEEPSEEK`
- **THEN** 系统使用 `LLM_API_KEY_DEEPSEEK` 的值作为 API key，忽略 `LLM_API_KEY`

#### Scenario: Fall back to shared key

- **WHEN** `LLM_PROVIDER=openai` 且未配置 `LLM_API_KEY_OPENAI`，但配置了 `LLM_API_KEY`
- **THEN** 系统使用 `LLM_API_KEY` 的值，保持向后兼容

#### Scenario: Reject missing credentials

- **WHEN** `LLM_PROVIDER=deepseek` 且 `LLM_API_KEY_DEEPSEEK` 与 `LLM_API_KEY` 均未配置
- **THEN** 系统拒绝启动或请求，并返回配置错误
