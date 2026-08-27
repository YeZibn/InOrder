# Tasks: Fix Responses reasoning delta leak

## 1. 修复累积逻辑

- [x] 1.1 在 `LLMClient.stream()` 中将文本累积、`received` 置位与增量回调收紧到 `event.event_type == "content_delta"` 分支内。
- [x] 1.2 增加单元测试：Responses 流包含 `response.reasoning_text.delta` 与 `response.output_text.delta` 混合事件时，最终文本仅含 `output_text.delta` 内容，回调不收到 reasoning 增量。
- [x] 1.3 增加单元测试：仅收到 reasoning delta 后抛可重试错误时，重试仍被允许；收到 content delta 后抛错则不重试。
- [x] 1.4 运行 LLM 客户端与流式相关测试，确认全量通过且 Chat Completions 路径行为不变。
