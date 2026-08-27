## 1. Provider 配置

- [x] 1.1 在 `LLMConfig` 和 `load_config` 中增加 `LLM_PROVIDER`，实现 `openai`/`deepseek` 校验与 OpenAI 默认兼容。
- [x] 1.2 按 provider 提供官方 base URL 默认值，并保留显式 `LLM_BASE_URL` 覆盖及服务根路径校验。
- [x] 1.3 为 provider-specific reasoning effort 和模型参数增加能力约束，避免发送目标接口不支持的字段。

## 2. Transport 与 Extractor 适配

- [x] 2.1 更新 OpenAI-compatible transport，根据 provider/API mode 构造 DeepSeek Chat Completions 与 Responses 请求。
- [x] 2.2 校验 Chat Completions/Responses 的 JSON 输出参数和终止状态，保持统一响应归一化。
- [x] 2.3 更新 LangExtract provider 初始化，使 DeepSeek 两种 API mode 使用正确的 OpenAI-compatible 地址和格式参数。

## 3. 文档与配置样例

- [x] 3.1 补充 `.env.example` 中的 provider、官方地址、模型和 API mode 配置说明，使用占位密钥。
- [x] 3.2 更新 README，说明 OpenAI/DeepSeek 四种 provider/API mode 组合、重启配置和安全注意事项。

## 4. 测试与验证

- [x] 4.1 增加 provider 默认值、非法值、DeepSeek 地址覆盖和 reasoning 参数校验测试。
- [x] 4.2 增加 OpenAI/DeepSeek Chat Completions 与 Responses 的请求构造和非流式归一化测试。
- [x] 4.3 增加两种 provider 的流式 chunks、终止事件、JSON 输出和 LangExtract provider 测试，并运行全量测试。

## 5. V4 事实性对齐

- [x] 5.1 在 `load_config` 中将 `LLM_REASONING_EFFORT` 校验放宽为 `None|low|medium|high|max`，覆盖 DeepSeek V4 思考模式的 `max` 值。
- [x] 5.2 在 `.env.example` 中补充 DeepSeek V4 模型名指引用及旧模型名废弃说明，使用占位密钥。
- [x] 5.3 将 `.env` 中 `LLM_MODEL` 从 `deepseek-chat` 更新为 `deepseek-v4-flash`，并补充配置分组注释。
- [x] 5.4 增加 `reasoning_effort=max` 的配置校验通过测试，并运行相关测试。

## 6. 按 provider 分离凭据

- [x] 6.1 在 `load_config` 中支持 `LLM_API_KEY_OPENAI`/`LLM_API_KEY_DEEPSEEK`，按 provider 选择 key，`LLM_API_KEY` 作为 fallback；缺少任何 key 时报配置错误。
- [x] 6.2 在 `.env.example` 和 `.env` 中补充 `LLM_API_KEY_OPENAI`/`LLM_API_KEY_DEEPSEEK` 配置项与注释。
- [x] 6.3 增加 provider-specific key 解析、fallback 与缺失报错的单元测试，并运行相关测试。
