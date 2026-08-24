## Why

项目当前主客户端仍通过 Chat Completions 调用上游，而目标中转站提供的是 Responses API。两套响应结构和请求协议不同，继续保留旧路径会造成接口不一致、错误排查困难，并可能导致部分链路无法调用。

## What Changes

- **BREAKING** 将 `LLMClient` 的文本调用统一迁移到 Responses API `/responses`。
- **BREAKING** 移除 Chat Completions transport、`choices[0].message.content` 解析和相关兼容路径。
- 使用 Responses API 的 `input`、`output_text` 及对应 usage 元数据完成统一响应转换。
- 保留现有重试、错误归一化、reasoning effort、回调输出和可注入测试边界。
- 让订单意图、rewrite 等调用自动使用新的 Responses transport。
- 让 LangExtract 配置与调用路径使用 Responses-compatible provider；不再依赖项目中的 Chat Completions transport。
- 更新 README、配置说明和测试，明确只支持 Responses API。

## Capabilities

### New Capabilities

- `responses-api-llm-transport`: 提供统一的 Responses API 请求、响应解析和错误处理边界。

### Modified Capabilities

- `llm-client`: 将文本模型调用协议从 Chat Completions 改为 Responses API，并移除旧协议支持。

## Impact

- 影响 `src/inorder_llm/infrastructure/llm/transport.py`、`client.py`、配置与模型适配。
- 影响 `src/inorder_llm/extract/langextract_adapter.py` 及 LangExtract provider 配置。
- 影响 CLI/意图/rewrite 的所有真实 LLM 调用，但不改变业务层 `LLMResponse` 接口。
- 依赖 OpenAI Python SDK 和 LangExtract 的 Responses API 兼容能力；若 LangExtract 版本不支持，需要项目内提供兼容 provider 适配。
