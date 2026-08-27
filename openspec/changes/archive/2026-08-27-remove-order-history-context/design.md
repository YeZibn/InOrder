## Context

当前代码已经具备多轮会话历史和 active `OrderContext`，但 Extract、时间归一化和意图规划仍保留历史订单专用语义。目标是一次性收敛领域模型：会话 history 仅表示当前会话消息，订单上下文仅表示当前草稿，时间实体仅表示当前订单的送达时间。

## Goals / Non-Goals

**Goals:**

- 让时间实体不再依赖 `new_order/history` 字段，避免缺少 context 导致归一化失败。
- 移除历史订单查询、历史订单号引用和历史时间分流的代码契约、Prompt、测试与文档。
- 保持基于 `HistoryConversation` 的多轮增量修改能力和 reference time 会话锚点。
- 让 API、CLI、LangGraph、SSE 和摘要输出使用一致的当前订单模型。

**Non-Goals:**

- 不实现历史订单查询、恢复历史订单或外部订单服务。
- 不删除 `HistoryConversation`、请求 `history` 字段或 Rewrite 的多轮上下文输入。
- 不改变车型模糊表达的拒绝策略，仅调整其历史指代命名。

## Decisions

### 1. 时间实体采用无上下文结构

删除 `context`、`VALID_CONTEXTS` 和 history 时间分支。时间归一化只验证 start/end、计算 fixed/range、添加时区并保留 raw。相比在缺失字段时默认补 `new_order`，直接删除字段能避免模型契约和运行时推断不一致。

### 2. 历史订单能力整体下线

从意图允许列表、Extract 实体类型、`OrderContext` 字段和 reducer 映射中删除 `query_history_order`、`order_id`、`referenced_order_id`。这样不会保留无法执行的半成品能力，也避免历史订单信息误写入当前草稿。

### 3. 会话 history 与历史订单严格分层

`HistoryConversation` 继续作为当前会话的消息上下文，供 Rewrite 处理“再加”“改成”“刚才提到”等多轮表达；它不再被解释为历史订单数据。遇到“恢复上次订单”等未支持表达时，不生成历史订单实体或字段。

### 4. 兼容迁移策略

对外 API 保留 `history`、`order_context` 和 `reference_time` 字段，保证 Java 调用方和前端请求契约稳定；`order_context` 中旧的 `referenced_order_id` 或时间 `context` 字段不再作为当前模型契约，代码可在入口忽略未知字段。主规格和文档同步更新，历史归档文件保持不变。

## Risks / Trade-offs

- [旧客户端仍发送历史订单字段] → API 入口只读取当前 dataclass 支持字段并忽略未知字段；不再将这些字段传入下游。
- [用户输入历史订单表达] → 明确作为当前版本不支持的语义，不猜测、不修改 OrderContext；通过 Prompt 和测试固定边界。
- [删除 order_id 影响旧快照反序列化] → 当前项目没有持久化迁移要求；升级说明中标注该 breaking change。

## Migration Plan

1. 先更新时间、意图、Extract、Reducer、摘要和模型字段。
2. 删除历史订单相关测试并补充当前订单时间与多轮 HistoryConversation 测试。
3. 更新 README、主 OpenSpec 和 Prompt changelog。
4. 运行全量测试及严格规格校验。

回滚时恢复上述字段和历史订单契约即可；不涉及数据库迁移或外部服务变更。
