## Context

当前 `reference_time` 在 CLI/HTTP 请求边界解析后仅存在于 LangGraph state，`OrderContext` 没有保存该值。Python 服务本身保持无状态，跨请求复用依赖调用方回传完整 `OrderContext`。

## Goals / Non-Goals

**Goals:**

- 为订单上下文增加可选的会话级时间锚点并保持向后兼容。
- 在请求入口统一实现上下文值、请求值和当前时间的优先级解析。
- 让 CLI 与 HTTP/SSE 在返回上下文时携带已确定的锚点，供后续轮次复用。
- 保证工作流内所有节点及重试使用同一时间值。

**Non-Goals:**

- 不在 Python 侧按 `session_id` 建立跨请求存储。
- 不改变相对时间的具体归一规则。
- 不引入 checkpoint、断点续跑或外部持久化组件。

## Decisions

### 1. 将时间锚点作为 OrderContext 字段

在 `OrderContext` 增加可选 `reference_time`，默认为空并参与 `to_dict()` 序列化。这样 Java/调用方只需持久化现有上下文即可带回时间锚点；旧上下文缺少该字段时按空值兼容。

### 2. 统一优先级解析

请求入口使用以下优先级：

```text
OrderContext.reference_time
    > request.reference_time
    > current Asia/Shanghai time
```

上下文已有值时不接受后续请求覆盖，避免同一会话的相对时间语义漂移。所有值均经过既有格式校验。

### 3. 在入口写入上下文，在 state 中传递

CLI 在调用 runner 前确保当前 session 的 `OrderContext.reference_time` 已确定；HTTP 在构造 LangGraph state 前将解析后的时间同步到传入上下文副本。工作流节点继续读取 state 中的字符串，不自行访问时钟。

### 4. 保持纯函数和无状态边界

时间解析与上下文复制均在请求范围内完成，不增加全局缓存。`OrderContextReducer` 不根据普通实体修改该字段，避免业务实体误覆盖会话时间锚点；只有请求入口负责初始化或保留它。

### 5. 清空即重置

CLI `/clear` 创建新的空 `OrderContext`，自然清除时间锚点。HTTP 调用方如需重置会话，应传入不含 `reference_time` 的新上下文。

## Risks / Trade-offs

- [长会话时间过期] → 同一会话跨天后“明天”等表达仍相对于首次锚点解释；通过新建 session 或清空上下文显式重置。
- [旧调用方上下文缺少字段] → 读取时按 `None`/空值处理并自动生成，不影响旧请求。
- [请求级时间与上下文冲突] → 明确上下文优先并可在接口文档中说明，避免隐式覆盖。
- [并发请求写入竞态] → Python 不共享跨请求 session；调用方应以其持久化层的版本或顺序保证同一会话更新不丢失。

## Migration Plan

1. 部署兼容的新字段；旧 `OrderContext` JSON 无需迁移即可读取。
2. 更新 CLI/API 测试，覆盖首轮生成、后续复用、显式时间和清空重置。
3. 调用方开始持久化并回传 `reference_time`；回滚时忽略该可选字段即可。
