## Context

当前 IntentGraph 和 OrderProcessingGraph 已经是独立编译的 LangGraph，但 full 链路由 `FullChainRunner` 手工串联。此次改造只补充父图编排层，不改变两个子图内部节点拓扑。

## Goals / Non-Goals

**Goals:**

- 新增统一的父图状态和 MainGraph。
- 以 LangGraph 原生子图节点挂载 IntentGraph 与 OrderProcessingGraph。
- 让 full CLI 直接调用 MainGraph，同时保留 intent/order 独立调用。
- 维持现有 full 输出结构和 OrderContext 保存行为。

**Non-Goals:**

- 不实现 QA 对话能力。
- 不实现历史订单服务、草稿服务、下单 API 或确认节点。
- 不重写意图或订单子图内部节点。

## Decisions

1. **MainGraph 作为独立 graph 模块。** 父图拥有自己的 state、routing 和 finalize 节点，避免继续扩展 CLI runner 的编排责任。
2. **子图通过 LangGraph 节点挂载。** 父图只依赖子图的输入输出字段，不复制 rewrite、extract 或意图校验逻辑。
3. **父图保留兼容结果包装。** 最终输出同时保留 `intent_result`、`order_result`，减少 CLI 格式和 session 更新改动。
4. **父图只按主意图路由。** 子意图计划本次只随意图结果传递，不提前实现历史订单或草稿业务分流。

## Risks / Trade-offs

- [子图 TypedDict 字段合并] → 设计显式父图 state，并为输入输出增加结构测试。
- [LangGraph 子图编译对象兼容性] → 使用最小 fake 子图和真实 compiled graph 分别测试。
- [full 输出回归] → 保留现有 result wrapper，并运行完整 CLI 测试。
- [错误部分结果] → 父图不捕获并吞掉子图异常，统一向上抛出。

## Migration Plan

先新增 MainGraph 并让 full runner 使用它；intent/order 入口保持原实现。验证通过后可移除 FullChainRunner 中的旧手工编排，但保留兼容类型或逐步收敛。
