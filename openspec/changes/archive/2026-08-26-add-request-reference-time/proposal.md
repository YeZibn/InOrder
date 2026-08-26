## Why

当前 CLI 在 session 初始化时生成参考时间，HTTP API 在未传入时则可能使用空字符串，导致长时间运行的会话使用过期时间，或 Extract 无法解析相对时间。需要将参考时间统一定义为单条用户消息的请求级时间锚点。

## What Changes

- 每条用户消息进入 CLI 或 HTTP API 时确定一次 `reference_time`。
- 调用方显式传入的参考时间优先使用；未传入时由 Python 使用 `Asia/Shanghai` 当前时间生成。
- 将确定后的时间写入工作流 state，Rewrite、Extract 以及结构化修复重试复用同一个值。
- 校验参考时间格式，避免将空字符串传入时间解析器。
- 不把 `reference_time` 写入订单业务字段，不在每个节点或每次重试时重新生成。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `order-entity-extraction`: 明确参考时间由请求入口确定，并作为稳定时间锚点传入提取流程。
- `workflow-sse-events`: HTTP 请求未提供参考时间时自动生成有效默认值，并将其用于本次工作流。
- `cli-chain-entrypoints`: CLI 每轮用户消息使用独立且稳定的参考时间，不复用 session 创建时的旧时间。

## Impact

- 影响 CLI 消息入口、SSE API 请求模型、LangGraph state 以及 Rewrite/Extract 的参数传递。
- 不改变订单字段 schema，不引入外部依赖或持久化。
- 需要补充 API、CLI、跨节点传递和时间边界测试。
