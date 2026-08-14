## Why

当前意图规划实现虽然按方法划分了主意图和子意图识别，但尚未真正使用 LangGraph 的 StateGraph、节点和条件边，无法验证主图/子图架构的路由行为。现在先搭建可编译、可测试的 LangGraph 骨架，为后续接入真实识别提示词和业务子图提供稳定入口。

## What Changes

- 引入 LangGraph 运行时依赖。
- 使用 TypedDict 定义意图图状态。
- 建立真正独立的 `main_intent_node` 和 `sub_intent_node`。
- 建立 `order / qa / ambiguous` 条件路由。
- 建立计划构建、校验、澄清和统一结束节点。
- 提供可编译的 Intent StateGraph 入口和 mock 路由测试。
- 本阶段不连接真实订单服务、不查询历史订单、不修改草稿、不创建订单、不回答问答。

## Capabilities

### New Capabilities

- `langgraph-intent-graph`: 提供基于 LangGraph 的意图识别图骨架和条件路由能力。

### Modified Capabilities

无。

## Impact

- 修改 Python 项目依赖，增加 LangGraph。
- 新增意图图 state、nodes、routing 和 graph builder 模块。
- 复用已有 `IntentPlan`、校验逻辑和 LLM 注入边界。
- 后续调用方将从 facade 迁移到编译后的 graph 入口。
