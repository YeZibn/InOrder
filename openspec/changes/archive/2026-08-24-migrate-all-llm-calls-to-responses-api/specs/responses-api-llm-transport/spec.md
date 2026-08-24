## Purpose

为项目提供可选的 Responses API 模型调用通道，统一请求构造、响应文本提取、usage 映射和上游错误处理，并允许通过环境配置在两种兼容接口之间切换。

## ADDED Requirements

### Requirement: Send requests through selected API

系统 SHALL 使用配置的 base URL、模型和 API key，根据 `LLM_API_MODE` 通过 `responses.create` 或 `chat.completions.create` 发送模型请求；`LLM_BASE_URL` 只表示服务根路径。

#### Scenario: Send a text request
- **WHEN** 调用方提供有效的角色消息列表
- **THEN** transport 将其转换为 Responses API 支持的 `input` 并发起请求

#### Scenario: Forward reasoning effort
- **WHEN** 配置包含 `low`、`medium` 或 `high` reasoning effort
- **THEN** transport 将对应格式的思考强度参数传递给所选接口

### Requirement: Normalize Responses output

系统 SHALL 从 Responses API 的 `output_text` 提取文本，并映射模型标识、usage、响应 id、完成原因和 refusal 等可用元数据到统一响应对象。

#### Scenario: Successful response
- **WHEN** Responses API 返回带有 output text 的成功响应
- **THEN** 调用方获得与现有 `LLMResponse` 兼容的文本和元数据

#### Scenario: Empty output
- **WHEN** Responses API 成功但没有可用 output text
- **THEN** 系统返回空文本而不读取 Chat Completions 的 choices 字段

### Requirement: Normalize both API outputs

系统 SHALL 将 Chat Completions 的 `choices[0].message.content` 和 Responses 的 `output_text` 都映射为统一响应对象。

#### Scenario: Select Chat Completions mode
- **WHEN** `LLM_API_MODE=chat_completions`
- **THEN** 请求发送至 `/chat/completions` 并解析 choices 响应

#### Scenario: Select Responses mode
- **WHEN** `LLM_API_MODE=responses`
- **THEN** 请求发送至 `/responses` 并解析 output text 响应
