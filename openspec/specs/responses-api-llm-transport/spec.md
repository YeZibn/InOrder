# responses-api-llm-transport Specification

## Purpose

为项目提供可选的 Responses API 模型调用通道，统一请求构造、响应文本提取、usage 映射和上游错误处理，并允许通过环境配置在两种兼容接口之间切换。

## Requirements

### Requirement: Send requests through selected API

系统 SHALL 根据 `LLM_API_MODE` 通过 Responses 或 Chat Completions 接口发送请求；`LLM_BASE_URL` 只表示服务根路径。

#### Scenario: Select Chat Completions mode
- **WHEN** `LLM_API_MODE=chat_completions`
- **THEN** 请求发送至 `/chat/completions` 并解析 choices 响应

#### Scenario: Select Responses mode
- **WHEN** `LLM_API_MODE=responses`
- **THEN** 请求发送至 `/responses` 并解析 output text 响应

### Requirement: Normalize both API outputs

系统 SHALL 将两种接口的文本、模型标识和 usage 映射为统一响应对象。

#### Scenario: Normalize successful output
- **WHEN** 任一所选接口返回成功
- **THEN** 调用方获得统一的文本结果和可用 token 使用量

#### Scenario: Forward reasoning effort
- **WHEN** 配置包含合法 reasoning effort
- **THEN** transport 按所选接口要求传递对应参数
