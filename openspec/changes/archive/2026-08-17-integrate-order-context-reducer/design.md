## Context

订单处理子图当前在 extract 后直接 finalize，只返回 rewrite 结果和实体列表；`OrderContextReducer` 已经提供按实体 action 生成新上下文的纯内存逻辑，但尚未成为图输出的一部分。CLI 的 `CliSession` 持有当前上下文，runner 是图结果与 CLI session 之间的适配边界。

## Goals / Non-Goals

**Goals:**

- 在 extract 成功后基于输入上下文和实体生成新的 `OrderContext`。
- 澄清路径和结构化失败路径不产生上下文更新。
- 让 order/full runner 将新上下文写回当前 CLI session。
- 保持输入对象不变，便于 LangGraph 节点测试和重试。
- 暴露足够的状态用于观察上下文是否更新。

**Non-Goals:**

- 不新增归一化规则或订单字段。
- 不实现 session 切换、文件/数据库持久化、`/context`、`/conversation`。
- 不调用历史订单、下单、选车或确认接口。

## Decisions

1. **在订单图中增加独立的上下文更新阶段。**
   extract 输出实体后进入 context update node，再进入 finalize。该节点调用现有 `OrderContextReducer.apply(old_context, entities)`，返回新对象；不直接修改 state 中的原对象。

2. **澄清路径保留原上下文。**
   clarification node 输出空实体并显式保留输入 `order_context`，finalize 返回原上下文，避免不完整请求污染订单草稿。

3. **runner 负责 session 写回。**
   `OrderChainRunner` 从图结果读取 `order_context`，保留在结果中；CLI 在 order/full 处理成功后将其赋给 `self.session.order_context`。图不依赖 CLI 具体实现。

4. **以结果字段表示更新状态。**
   结果增加 `order_context_updated`，由是否执行上下文更新且结果与输入上下文不同决定；CLI 输出该状态和实体数量。上下文本身仍作为结构化对象返回。

5. **错误保持显式失败。**
   reducer 的 `ContextReductionError` 或已有 normalization 错误向上抛出，不写回旧 session，也不返回部分上下文，便于发现简单样例之外的数据问题。

6. **兼容现有 graph 输入输出。**
   既有 `entities`、`rewrite_result`、澄清字段继续保留；新增 `order_context` 和更新状态，不改变 rewrite/extract 协议。

## Risks / Trade-offs

- [Risk] 未归一化或不完整实体可能导致 reducer/normalizer 抛错 → 保持异常可见，后续单独补归一化与容错策略。
- [Risk] CLI 写回只在调用成功后发生，异常轮次不会保留部分结果 → 这是保护草稿一致性的预期行为。
- [Risk] 当前 history 仍可能只记录用户输入 → 本 change 不扩展对话记录策略，后续单独处理。

