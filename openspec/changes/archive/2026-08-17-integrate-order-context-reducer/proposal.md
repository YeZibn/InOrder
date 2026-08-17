## Why

当前订单处理链路已经完成 rewrite 和 extract，但提取出的实体尚未应用到当前订单上下文，导致 CLI 多轮输入只能观察解析结果，不能持续维护订单草稿。现在需要先打通“订单语义解析 → 内存订单草稿更新”的最小闭环，便于用简单样例验证多轮下单效果。

## What Changes

- 在订单处理子图中接入现有 `OrderContextReducer`，将 extract 返回的实体应用到传入的 `OrderContext`，并返回更新后的上下文。
- 在 CLI 的 `order` 和 `full` 链路中持久化本轮返回的 `order_context` 到当前内存 session。
- 在链路输出中展示上下文是否已更新，便于调试连续下单输入。
- 保持解析边界：不查询历史订单、不创建订单、不确认下单、不引入数据库持久化。
- 暂不新增复杂归一化规则；沿用 `OrderContextReducer` 内部已有 normalization 行为。

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `order-processing-subgraph`: 订单处理子图在 extract 后应用 `OrderContextReducer` 并返回更新后的订单上下文。
- `cli-chain-entrypoints`: CLI 在 order/full 链路中保存订单处理子图返回的上下文到当前内存 session，并暴露上下文更新状态。

## Impact

- Affected code:
  - `src/inorder_llm/graph/order/`
  - `src/inorder_llm/cli/runners.py`
  - `src/inorder_llm/cli/app.py`
  - related tests under `tests/`
- No new external dependencies.
- No database, order API, history-order lookup, or real order submission side effects.

