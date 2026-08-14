## Context

现有 `intent_planning` 模块已经提供 IntentPlan 数据模型、计划校验和可注入模型，但其执行器是顺序 facade，不是真正的 LangGraph 图。该 change 将其包装为编译后的 StateGraph，保留识别-only 边界。详见 proposal.md 和 specs/langgraph-intent-graph/spec.md。

## Goals / Non-Goals

**Goals:**

- 引入 LangGraph 并建立可编译的 StateGraph。
- 将主意图和子意图实现为两个真实、可观测的节点。
- 使用 conditional edges 表达 order、qa、ambiguous 路由。
- 统一所有分支的状态输出，支持 mock 测试。

**Non-Goals:**

- 不实现真实 LLM prompt 优化或结构化输出供应商适配。
- 不连接订单数据库、订单 API、问答知识库或业务工具。
- 不实现 checkpoint、interrupt、流式执行、并行分支或业务子图。

## Decisions

### 使用 LangGraph StateGraph 作为唯一图编排边界

相比继续维护手工 `invoke` 循环，StateGraph 能显式表达节点、条件边、结束节点和后续可嵌套子图的边界。现有 facade 可保留作为兼容层，但新入口必须返回编译后的 graph。

### 两个识别节点严格分工

`main_intent_node` 只识别 `order/qa/ambiguous`；仅当路由结果为 `order` 时，`sub_intent_node` 才识别订单多子意图。计划构建和校验属于后置确定性节点，不与识别节点合并。

### 统一 TypedDict 状态

图状态使用 TypedDict，包含 message、main_intent、confidence、sub_intents、intent_plan、needs_clarification 和 clarification_reason。这样节点可以返回局部更新，符合 LangGraph 的状态合并模型。

### 使用依赖注入替代真实业务工具

Graph builder 接受意图识别器作为依赖，测试使用 fake resolver。当前节点只能读取识别器结果，禁止注入订单查询或修改工具，确保骨架没有业务副作用。

### 路由分支

```text
START → main_intent
             ├─ order → sub_intent → build_plan → validate_plan → finalize → END
             ├─ qa → build_plan → finalize → END
             └─ ambiguous → clarification → finalize → END
```

## Risks / Trade-offs

- [LangGraph 版本 API 变化] → 锁定兼容范围并在 conda agent 环境执行编译测试。
- [旧 facade 与新 graph 并存造成入口混淆] → README 明确编译 graph 为新入口，facade 仅保留兼容用途。
- [mock 路由掩盖真实 LLM 输出问题] → 本 change 只验证图结构；真实 prompt 和输出契约另立 change。

## Migration Plan

先安装 LangGraph 依赖并以 mock resolver 验证新 graph；调用方逐步改用 graph builder。现有 `IntentPlanningSubgraph` 暂不删除，确认新入口稳定后再单独清理。

## Open Questions

无。真实 LLM 结构化输出和 LangGraph checkpoint 可在后续 change 中单独决定。
