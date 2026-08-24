## MODIFIED Requirements

### Requirement: Text chat completion

系统 SHALL 接受包含角色和文本内容的消息列表，并根据 `LLM_API_MODE` 选择 Chat Completions 或 Responses API，返回统一结构的文本结果；未配置时默认使用 `chat_completions`。

#### Scenario: Successful completion
- **WHEN** 调用方提供有效消息列表且所选上游接口返回成功
- **THEN** 系统返回生成文本、模型标识以及可用的 token 使用量

#### Scenario: Empty messages
- **WHEN** 调用方提供空消息列表
- **THEN** 系统在发起请求前返回参数错误

#### Scenario: Reasoning effort is forwarded when configured
- **WHEN** 调用方使用已配置 reasoning effort 的客户端发送消息
- **THEN** 客户端向所选接口传递对应的思考强度参数

#### Scenario: Reasoning effort is omitted when unset
- **WHEN** 调用方未配置 reasoning effort
- **THEN** 客户端不向所选接口添加该可选参数

#### Scenario: Select API mode from environment
- **WHEN** `LLM_API_MODE` 为 `chat_completions` 或 `responses`
- **THEN** 客户端调用对应接口；未配置时使用 `chat_completions`

#### Scenario: Reject unsupported API mode
- **WHEN** `LLM_API_MODE` 为其他值
- **THEN** 客户端在发起请求前返回配置错误
