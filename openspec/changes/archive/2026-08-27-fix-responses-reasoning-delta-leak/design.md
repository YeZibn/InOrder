# Design: Fix Responses reasoning delta leak

## Context

DeepSeek V4 接入后开启 Responses 流式模式，实测（诊断脚本消费 transport 原始流）确认事件协议规范：思维链走 `response.reasoning_text.delta`，最终答案走 `response.output_text.delta`。`_stream_event()` 的归一化已正确区分两者——只有 `output_text.delta` 被标记为 `content_delta`，reasoning 事件保留原始类型。

缺陷在 `LLMClient.stream()` 的累积循环：`if event.delta:` 只判断 delta 非空，未检查 `event_type`。reasoning 事件的 delta 字段非空，因此被拼进 `chunks` 并触发回调。

## Goals / Non-Goals

**Goals:**
- 最终文本与增量回调只包含内容增量。
- `received` 重试标记只反映内容增量交付状态。

**Non-Goals:**
- 不透传 reasoning 内容给上层（未来如需思维链展示，另行变更）。
- 不修改 `_stream_event` 的归一化映射。
- 不改动 Chat Completions 路径。

## Decisions

1. **在 `stream()` 累积处按类型过滤。** 将 `if event.delta:` 收紧为 `if event.event_type == "content_delta" and event.delta:`。修复点单一、位于消费端，`_stream_event` 保持生产端语义不变；Chat Completions 的 content delta 同样被归一化为 `content_delta`，行为不变。
2. **`received` 标记与累积同条件置位。** reasoning delta 到达不代表已向调用方交付内容，不应阻断重试；与累积使用同一判断，避免两处语义漂移。
3. **回调与累积共用同一守卫。** `callback(event.delta)` 移入同一 `content_delta` 分支内，确保 CLI 输出与最终文本一致。

## Risks / Trade-offs

- [回调方依赖 reasoning 输出做调试] → 当前无此类调用方；如需调试推理过程，应走显式事件通道而非 content 回调，留待未来变更。
- [某些网关把内容放在非标准事件类型里] → 现有 `_stream_event` 已把它们归一化为 `content_delta` 或忽略，过滤条件不感知具体类型名，无新增风险。

## Migration Plan

单点修复，无需迁移。部署后 Responses 流式模式的 `response.text` 立即恢复为纯内容文本，结构化 JSON 解析随之恢复。

## Open Issues

无。
