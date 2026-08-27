## Why

当前订单流程已经不执行历史订单查询，但时间实体、意图规划、订单号和车型指代仍残留 `new_order/history` 语义。该残留会要求模型输出无用字段，并可能让不完整的时间实体在归一化阶段触发异常；现在统一收敛为“当前会话 + 当前订单”的模型。

## What Changes

- **BREAKING** 删除时间实体 `context` 字段及 `new_order/history` 分流；送达时间仅由 `start`、`end`、`kind`、`timezone` 和 `raw` 表示。
- **BREAKING** 删除历史订单查询子意图 `query_history_order`、订单号历史引用实体 `order_id` 和 `OrderContext.referenced_order_id`。
- 清理 Extract、Rewrite、订单摘要、Reducer、车型匹配数据集中的历史订单语义与示例。
- 保留 `HistoryConversation`、API `history` 和 Rewrite 的多轮会话输入；它们只表示当前会话消息，不代表历史订单数据。
- 更新测试、README、OpenSpec 主规格和 Prompt 变更记录，确保不再要求或产生上述历史订单字段。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `order-entity-extraction`：移除时间上下文标记、历史订单实体及历史订单提取场景。
- `order-time-normalization`：仅校验和归一化当前订单时间边界。
- `intent-planning`：子意图只保留创建订单草稿和修改当前草稿。
- `order-rewrite`：只基于当前订单上下文和当前会话历史处理多轮省略，不解析历史订单引用。
- `order-processing-subgraph`：订单解析边界不再包含历史订单语义。
- `conversation-order-context`：当前订单上下文不再保存历史订单引用字段。
- `order-completeness-summary`：送达时间判断不再依赖历史时间上下文。

## Impact

影响 Extract/归一化/reducer、意图 Prompt 与校验、Rewrite Prompt、订单摘要、车型匹配离线数据集、相关单元测试和文档。API 的 `history` 请求字段、`HistoryConversation` 类型及多轮订单修改能力保持不变；不引入新依赖或外部服务。
