## Why

订单处理图中的 `OrderContext`、本轮 `Entity` 和 `GraphState` 目前缺少清楚的职责边界：Reducer 和车型节点分别归一化实体，MainGraph 的结果又同时暴露根级与 `order_result` 内的订单上下文。调用方因此需要猜测应读哪份状态，下游节点也容易误用旧上下文。

本变更明确唯一的跨轮订单状态和本轮工作状态，统一实体处理顺序与订单结果出口，让每个节点都基于同一份最新工作上下文。

## What Changes

- 明确 `OrderContext` 是唯一跨轮订单业务快照；`GraphState` 是本轮执行工作区，只持有一份工作中的 `OrderContext`，并分别承载请求、本轮实体、派生结果和内部控制信息。
- Extract 后增加唯一的实体归一化图节点，统一调度现有的时间、手机号、枚举、车型/规格归一化规则；各领域规则仍由独立函数实现。节点保留原始表达、action 和车型匹配状态，ContextUpdate 与 VehicleResolution 共用同一份归一化结果。该节点只规范实体值，不负责 action 合并、货物画像、城市目录查询或车型估算；ContextUpdate 紧接其后更新工作中的 `OrderContext`。Reducer 改为只接收已归一化实体；直接调用 `OrderContextReducer.apply` 的调用方和测试需迁移为先归一化再应用 action。
- 将订单上下文 Reducer 放在归一化之后、货物画像和车型处理之前。下游业务节点读取更新后的工作上下文；只有整条工作流成功后，调用方才保存最终快照。
- 统一订单链路 Runner 的返回形状，使 order 与 full 链路都通过 `order_result.order_context` 暴露本轮最终上下文，不再额外暴露根级重复上下文。**BREAKING**：依赖 `OrderChainRunner` 根级订单字段或 MainGraph 根级 `order_context` 的调用方需要迁移到 `order_result`。
- 保持现有车型匹配、用户车型优先、`lower_bound_fit`/`upper_bound_only` 提交规则及 SSE 业务阶段语义不变。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `order-processing-subgraph`：规定实体只归一化一次、Reducer 的执行时机、节点读取当前工作上下文以及子图的输入/输出边界。
- `conversation-order-context`：明确跨轮 `OrderContext` 与本轮实体指令的职责、Reducer 只应用已归一化实体的输入契约，以及成功后才提交最终快照的边界。
- `main-parent-graph`：明确父图内部工作状态与调用方订单结果的边界，并统一唯一的 context 返回位置。
- `cli-chain-entrypoints`：统一 order/full Runner 结果结构，并规定 CLI 从同一结果路径保存会话上下文。

## Impact

- 主要代码：`graph/order/state.py`、订单处理节点与图构建、`context/reducer.py`、`graph/main/state.py`、MainGraph 结果组装、CLI runners/app，以及相关 workflow 结果适配。
- 主要调用契约：`OrderChainRunner` 与 `FullChainRunner` 的订单结果读取路径；SSE 对外事件协议和车型业务规则不变。
- **BREAKING**：`OrderContextReducer.apply` 的输入契约改为已归一化实体；直接调用方必须显式先执行统一实体归一化，再应用 action。
- 需要补充针对实体归一化复用、Reducer 顺序、失败不提交、Runner 结果一致性和会话持久化路径的测试。
