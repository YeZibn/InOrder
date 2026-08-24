## Context

当前 `LLMClient` 以 Chat Completions 的 `messages` 请求和 `choices[0].message.content` 响应为基础；LangExtract 1.6.0 的 OpenAI provider 也固定使用 Chat Completions。业务层已经通过 `LLMResponse` 隔离供应商响应，因此迁移可以集中在基础 transport 和抽取 provider 边界。

## Goals / Non-Goals

**Goals:**

- 以 OpenAI SDK 的 Responses API 为唯一生产调用协议。
- 保持 `LLMClient.chat()`、`LLMResponse`、重试和错误类型对业务层的兼容。
- 为 LangExtract 提供使用 Responses API 的适配实现，并保留 grounded extraction 行为。
- 通过可注入 transport/provider 覆盖请求和响应解析测试。

**Non-Goals:**

- 不改变意图、rewrite、extract 的 prompt 或业务 schema。
- 不引入流式响应、Responses API tools 或会话状态管理。
- 不同时维护 Chat Completions fallback。

## Decisions

1. **统一使用 Responses API transport**：在 transport 中调用 `client.responses.create(input=..., model=...)`，将现有 `ChatMessage` 转换为 Responses API 的输入项。选择单一协议是为了避免根据网关能力猜测和双路径行为差异；不保留 Chat Completions fallback。

2. **在客户端统一归一化响应**：从 SDK response 的 `output_text` 读取文本，从 `usage` 读取 `input_tokens`、`output_tokens` 和 `total_tokens`，其余元数据按可选字段安全读取。业务层继续只依赖 `LLMResponse`。

3. **LangExtract 使用独立 Responses provider**：不修改 LangExtract 的业务抽取映射；复制其必要的 prompt/schema/解析边界，改用 Responses API 发送请求并将 `output_text` 转成 LangExtract 期望的 JSON/YAML 结果。若 provider 接口允许注入，将 provider 作为 adapter 传入，便于测试。

4. **配置保持 base URL 为服务根路径**：`LLM_BASE_URL` 仍为 `.../v1`，由 SDK 的 Responses resource 追加 `/responses`；禁止把 endpoint 路径写入环境变量。

## Risks / Trade-offs

- [Responses API 与中转站实现存在字段差异] → 增加请求快照和响应 shape 单测，并在真实网关探针中打印安全的响应摘要。
- [LangExtract 1.6.0 内置 provider 依赖 Chat Completions] → 使用项目内 provider 适配，不让生产链路隐式回退旧 endpoint。
- [Responses usage 字段与旧字段命名不同] → 在 transport 内完成字段映射，缺失字段保留为 `None`。
- [旧的第三方 transport 注入代码依赖 choices shape] → 将其视为 breaking change，在测试和 README 中明确迁移到 Responses response fixture。

## Migration Plan

1. 实现 Responses transport 和统一响应归一化。
2. 替换 LangExtract OpenAI 调用边界并补充 fixture 测试。
3. 更新 CLI/README/环境变量说明和旧接口测试。
4. 在 conda `agent` 环境运行完整测试；使用显式环境变量执行可选真实网关探针。

## Open Questions

无。Responses API 是本次变更的唯一目标协议，旧 Chat Completions 路径不保留。
