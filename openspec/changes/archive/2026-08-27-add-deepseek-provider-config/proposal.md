## Why

当前 LLM 配置只表达接口模式，无法明确区分 OpenAI 与 DeepSeek 官网服务，导致供应商默认地址、模型能力和推理参数容易配置错误。增加显式 provider 配置后，可以在不改业务工作流的前提下安全切换两家 OpenAI-compatible 服务。

## What Changes

- 增加 `LLM_PROVIDER` 配置，支持 `openai` 和 `deepseek`，并校验非法值。
- 为 provider 提供官网默认 base URL，同时允许显式 `LLM_BASE_URL` 覆盖，保持 endpoint 由 `LLM_API_MODE` 选择。
- 适配 DeepSeek 官方 Chat Completions 与 Responses API 的请求参数、模型和推理配置差异。
- 支持按 provider 分离 API Key（`LLM_API_KEY_OPENAI`/`LLM_API_KEY_DEEPSEEK`），`LLM_API_KEY` 作为向后兼容 fallback。
- 保持统一的 `LLMClient`、重试、流式、结构化输出和 LangExtract 调用抽象。
- 补充 `.env.example`、README 配置说明及 OpenAI/DeepSeek 两种 provider 的单元测试矩阵。
- 不在代码、文档或测试中写入真实 API Key；仅通过环境变量注入凭据。

## Capabilities

### New Capabilities

- `llm-provider-configuration`: 配置并选择 OpenAI 或 DeepSeek 服务及其官方 API 地址。

### Modified Capabilities

- `llm-client`: 增加 provider 配置读取、校验及 provider-specific 参数约束，同时保持统一客户端结果。
- `responses-api-llm-transport`: 根据 provider 与 API mode 正确构造 Chat Completions/Responses 请求。
- `llm-streaming`: 验证两个 provider 的流式响应均能归一化为统一增量事件。

## Impact

- 影响 `LLMConfig`、配置加载、OpenAI-compatible transport 和 LangExtract provider 初始化。
- 影响 `.env.example` 与 README 的环境变量文档。
- 增加配置及 transport 测试，不改变意图识别、订单解析、货物画像和车型模块接口。
