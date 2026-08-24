## Why

当前 LLM 客户端等待完整响应后才通知调用方，CLI 无法展示模型生成进度。中转站已经验证同时支持 Chat Completions 和 Responses 的 SSE 流式接口，因此需要把流式能力接入本地客户端，同时保持现有结构化 resolver 的完整响应行为不变。

## What Changes

- 新增统一的 LLM 流式事件模型和 `LLMClient.stream` 调用入口。
- 为 Chat Completions 与 Responses 分别实现 SSE 增量内容解析，并统一为同一种回调/事件语义。
- CLI 支持实时显示 LLM 增量内容，保留现有完整结果和节点执行顺序。
- 流式请求结束后仍累积并返回完整 `LLMResponse`，供 JSON 解析和现有 resolver 使用。
- 明确流式请求的完成、失败、空增量和异常行为；首个增量到达后不重复重试。
- 增加两种 API 模式和流式解析的单元测试、CLI 输出测试。
- 兼容流式网关可能在 JSON 响应开头插入的 BOM/零宽字符，避免结构化 resolver 解析失败。

## Capabilities

### New Capabilities

- `llm-streaming`: 提供跨 Chat Completions/Responses 的统一流式 LLM 调用与 CLI 展示能力。

### Modified Capabilities

- `llm-client`: 增加流式调用接口，同时保持既有非流式调用兼容。
- `cli-chain-entrypoints`: 在现有三条链路中支持 LLM 增量内容输出，不改变链路选择和业务结果格式。

## Impact

- 主要影响 `infrastructure/llm`、CLI 启动与输出代码及其测试。
- 依赖 OpenAI-compatible SDK 的 Chat Completions/Responses 流式对象。
- LangGraph 节点仍以完整结果驱动；LangExtract、货物画像和车型计算本身不改为流式。
- 主要影响结构化 JSON 响应的清洗边界和相关测试，不修改 JSON 正文语义。
