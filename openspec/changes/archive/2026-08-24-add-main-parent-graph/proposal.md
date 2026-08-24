## Why

当前 full 链路由 Python `FullChainRunner` 顺序调用意图图和订单处理图，虽然已有两个 LangGraph 子图，但缺少真正的 LangGraph 父图统一路由、状态传递和结果汇总。新增父图可以让工作流结构与主意图 → 订单子图的业务关系一致，并保留 intent、order 独立调试入口。

## What Changes

- 新增 MainGraph 作为 full 链路的父图。
- 将现有 IntentGraph 和 OrderProcessingGraph 作为父图中的子图节点接入。
- 新增父图联合状态，统一传递消息、历史对话、订单上下文、参考时间和子图结果。
- 根据意图子图输出的 `main_intent` 路由到 order 子图或 QA 占位结束节点。
- 汇总为现有 CLI 兼容的 `intent_result`、`order_result` 结构。
- full 链路改为调用父图；intent 和 order 链路继续直接调用对应子图。
- 增加父图路由、状态传递、QA 分支、订单分支和 CLI 兼容测试。

## Capabilities

### New Capabilities

- `main-parent-graph`: 提供基于 LangGraph 父图和子图的完整链路编排能力。

### Modified Capabilities

- `cli-chain-entrypoints`: full 链路改由 MainGraph 执行，同时保持三条链路入口和输出兼容。
- `langgraph-intent-graph`: 意图图作为父图可挂载的意图子图，输出可供父图路由的结构化状态。
- `order-processing-subgraph`: 订单处理图作为父图可挂载的下单子图，接收父图传入的订单处理上下文。

## Impact

- 影响 `src/inorder_llm/graph`、CLI runner/启动入口及相关测试。
- 不实现 QA、历史订单、草稿修改、真实创建订单或确认下单。
- 不改变现有意图子图和订单子图内部节点顺序；不改变 intent/order 独立入口。
