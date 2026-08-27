# Fix Responses reasoning delta leak

## Why

DeepSeek V4 在 Responses 流式模式下默认输出思维链，事件序列为 `response.reasoning_text.delta`（思维链）与 `response.output_text.delta`（最终答案）两类独立事件。实测确认协议本身区分正确，但 `LLMClient.stream()` 累积文本时只判断 `event.delta` 是否非空、不检查 `event_type`，导致思维链 delta 被拼进 `response.text` 并通过回调打印到 CLI 控制台。后果：

- 结构化 JSON 解析失败（text 开头是思维链文字而非 JSON），意图分类崩溃。
- CLI 用户看到本不该暴露的内部思维链输出。
- `received` 重试标记被 reasoning delta 错误置位，压缩了可重试窗口。

## What Changes

- 修复 `LLMClient.stream()` 的累积逻辑：仅 `event_type == "content_delta"` 的事件参与文本累积与回调交付；`received` 标记同样只对 content delta 置位。
- 保持 `_stream_event` 归一化行为不变（reasoning 事件已正确保留原类型、未被标为 content_delta）。
- 不改变 Chat Completions 路径行为（该路径读 `delta.content`，天然不受 reasoning 字段影响）。
- 不引入思维链透传能力（不在本变更范围）。

## Capabilities

### Modified

- `llm-streaming`: 流式累积必须按事件类型过滤，reasoning delta 不得进入最终文本或增量回调。
