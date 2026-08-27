## Context

当前 `LLMConfig` 已支持 Chat Completions/Responses 双模式，transport 通过 OpenAI SDK 的两个 resource 调用兼容网关；但配置没有 provider 语义，无法为 DeepSeek 官网提供默认地址和参数能力约束。DeepSeek 官方接口均为无状态请求，业务层现有消息、重试和结果归一化模型可以继续复用。

## Goals / Non-Goals

**Goals:**

- 增加 provider 维度并保持现有 OpenAI 配置向后兼容。
- 为 provider 与 API mode 组合统一生成请求，同时过滤不被目标接口支持的可选参数。
- 覆盖非流式、流式、JSON 输出和 LangExtract 的 DeepSeek 路径。
- 通过环境变量配置，不在代码中保存凭据。

**Non-Goals:**

- 不重写业务图、提示词、重试策略或 SSE 协议。
- 不实现 DeepSeek 私有 SDK、工具调用扩展或供应商自动故障转移。
- 不将完整 endpoint 写入 `LLM_BASE_URL`，不改变无状态会话行为。

## Decisions

1. **独立 provider 与 API mode。** `LLM_PROVIDER` 只标识 `openai`/`deepseek`，`LLM_API_MODE` 继续独立选择 `chat_completions`/`responses`。这样可覆盖四种组合，避免将供应商和协议耦合。

2. **默认地址按 provider 解析。** OpenAI 默认使用 `https://api.openai.com/v1`，DeepSeek 默认使用 `https://api.deepseek.com`；显式 `LLM_BASE_URL` 优先，便于兼容网关和测试。transport 仍由 SDK 追加具体资源路径。

3. **能力参数在 transport 边界处理。** Chat Completions 使用 `messages`、`response_format` 和 provider 支持的 `reasoning_effort`；Responses 使用 `input`、`text.format` 和 `reasoning.effort`。不把 provider 判断散落到业务节点，统一在 config/transport 层完成。

4. **保留统一归一化。** Chat Completions chunks、Responses semantic SSE 以及最终响应均继续归一化为 `LLMResponse`/`LLMStreamEvent`；DeepSeek 的 `[DONE]` 和 `response.completed` 等终止信号由 transport/client 适配，不改变上层解析。

5. **显式配置推理参数。** 当前校验 `low|medium|high`；DeepSeek V4（2026-04 发布）后，思考模式通过 `thinking={"type":"enabled"}` 启用，`reasoning_effort` 仅接受 `high|max`，且响应包含 `reasoning_content` 字段需解析与多轮回传。旧模型名 `deepseek-chat`/`deepseek-reasoner` 已于 2026-07-24 废弃，应迁移到 `deepseek-v4-flash`/`deepseek-v4-pro`。完整的 V4 思维模式适配（thinking 参数、reasoning_content 解析与回传）不在本变更范围，需通过单独变更处理。

6. **按 provider 分离凭据。** 支持 `LLM_API_KEY_OPENAI` 和 `LLM_API_KEY_DEEPSEEK` 按 provider 独立配置 API Key；解析优先级为 `LLM_API_KEY_<PROVIDER>` > `LLM_API_KEY`。未配置任何 key 时 SHALL 报配置错误。保持 `LLM_API_KEY` 向后兼容，使现有单 key 部署无需改动。

## Risks / Trade-offs

- [DeepSeek 官网模型或参数版本变化] → 使用官网兼容字段，增加请求构造单测和可配置模型名，不硬编码模型能力。
- [V4 思维模式协议变化] → V4 引入 `thinking` 参数和 `reasoning_content` 字段；当前 transport 未发送 thinking 参数，未解析 reasoning_content，多轮工具调用可能触发 400 错误。需单独变更适配。
- [旧模型名废弃] → `deepseek-chat`/`deepseek-reasoner` 已于 2026-07-24 废弃；当前 .env 仍使用 `deepseek-chat`，需迁移到 `deepseek-v4-flash`/`deepseek-v4-pro`。
- [Responses 网关未完全兼容] → provider/API mode 可独立切换，默认先推荐 DeepSeek Chat Completions；失败时通过统一错误归一化反馈。
- [JSON schema 能力差异] → 首版保留 `json_object` 兼容路径，严格 schema 失败时由现有格式修复机制处理，不改变业务接口。
- [密钥泄露风险] → 文档只使用占位符，`.env` 不纳入版本控制，测试使用伪造 key。

## Migration Plan

保持未设置 `LLM_PROVIDER` 时的 OpenAI 默认行为。部署 DeepSeek 时新增 provider、API key 和模型配置并重启进程；先以非流式 Chat Completions 验证意图/订单结构化调用，再按需开启流式或切换 Responses。回滚时将 provider 改回 `openai` 或移除该变量即可。

注意：DeepSeek V4 发布后，旧模型名 `deepseek-chat`/`deepseek-reasoner` 已于 2026-07-24 废弃。`deepseek-chat` 当前指向 `deepseek-v4-flash` 非思考模式，`deepseek-reasoner` 指向 `deepseek-v4-flash` 思考模式；建议显式使用 `deepseek-v4-flash`/`deepseek-v4-pro` 避免依赖隐式映射。V4 思维模式（thinking 参数、reasoning_content 解析与回传）不在本变更范围内。
