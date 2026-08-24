## Context

当前 `LLMClient.chat()` 和 `OpenAITransport.complete()` 只等待完整响应；CLI 的 `on_content` 也只在响应归一化后触发一次。中转站已验证 Chat Completions 与 Responses 均返回可用 SSE，但两者事件格式不同。

## Goals / Non-Goals

**Goals:**

- 在 transport 层分别消费两种 API 的流式对象。
- 在 client 层统一增量回调、累积文本、完成结果和错误处理。
- 让 CLI 可配置地实时展示增量，同时保留现有 resolver 的完整 JSON 解析。

**Non-Goals:**

- 不改变 LangGraph 节点拓扑或同步执行语义。
- 不把 LangExtract 改造成流式 grounded extraction。
- 不让半截 JSON 提前进入下游 resolver。

## Decisions

1. **以完整结果为主、增量展示为辅。** `stream()` 在内部累积文本，完成后返回 `LLMResponse`；resolver 仍只消费完整文本。
2. **统一事件而非暴露 SDK 对象。** Chat Completions 的 `delta.content` 和 Responses 的 `response.output_text.delta` 映射到统一回调，避免业务层绑定供应商事件。
3. **首 token 后不重试。** 首个增量前的连接失败可以沿用重试；已经输出内容后失败必须终止，防止重复拼接。
4. **CLI 通过配置开关。** 默认保持现有行为，显式启用后才实时输出；节点边界由 CLI 在每次调用前后负责显示。
5. **只清洗结构化响应前缀。** 在交给 JSON resolver 解析前，移除文本开头的 UTF-8 BOM 和零宽格式字符（如 `\\ufeff`、`\\u200b`、`\\u200c`、`\\u200d`）；不清洗正文中间或 JSON 字符串值中的字符，避免改变用户内容。

## Risks / Trade-offs

- [半截 JSON] → 只展示增量，不提前解析；完成后才交给 resolver。
- [Responses 事件类型较多] → 只消费文本增量、完成和失败事件，忽略元数据与 reasoning 事件。
- [流式输出影响终端格式] → 使用明确的开始/结束标记，并保留最终结构化结果。
- [第三方 SDK 版本差异] → 通过注入式 transport 和事件 fixture 测试，不依赖真实网络测试。
- [网关插入不可见前缀] → 结构化解析入口统一执行前缀清洗，并增加字符级回归测试；CLI 原始增量展示仍保留原样。

## Migration Plan

先增加能力并默认关闭；验证两种 API 的单元测试和 CLI 手工测试后，通过环境变量启用。出现问题时关闭开关即可回退到现有非流式路径。
