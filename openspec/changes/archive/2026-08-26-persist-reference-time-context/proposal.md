## Why

当前 `reference_time` 只在单次 CLI 消息或 HTTP 请求边界生成，未写入 `OrderContext`，导致多轮对话中相对时间的计算锚点可能随请求变化。需要将首次确定的时间锚点随订单上下文传递并复用，保证“明天”“下周”等表达在同一会话内语义稳定。

## What Changes

- 为 `OrderContext` 增加可序列化的 `reference_time` 字段。
- 首次处理请求时按“上下文已有值、调用方传入值、当前 Asia/Shanghai 时间”的优先级确定时间，并写入订单上下文。
- 后续请求优先复用 `OrderContext.reference_time`，不因新请求或新消息重新获取当前时间。
- CLI 在每轮输入前读取并更新会话上下文中的时间锚点；`/clear` 清除该锚点。
- HTTP/SSE 接口在工作流开始前解析上下文时间，并在返回的 `OrderContext` 快照中携带最终值。
- Rewrite、Extract、货物画像、车型处理及其重试继续复用同一会话级时间锚点。
- 保留显式传入 `reference_time` 的兼容性；已有上下文时间优先于后续请求传入的不同值。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `conversation-order-context`：订单上下文持久化会话级 `reference_time`。
- `cli-chain-entrypoints`：CLI 按会话上下文复用时间锚点。
- `workflow-sse-events`：HTTP/SSE 请求读取、补充并返回上下文时间锚点。
- `order-entity-extraction`：提取阶段使用跨轮次稳定的上下文时间锚点。

## Impact

影响 `OrderContext` 数据模型、CLI session、HTTP/SSE 请求边界、LangGraph state 组装以及 Rewrite/Extract 的时间参数传递。调用方无需新增字段，但需要在后续请求中回传包含 `reference_time` 的最新 `order_context`；未传入旧上下文的请求仍可由 Python 自动生成时间。
