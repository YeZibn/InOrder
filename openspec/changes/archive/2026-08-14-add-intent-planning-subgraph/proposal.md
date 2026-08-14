## Why

后续主图和业务子图需要一个稳定的意图识别边界，将用户自然语言转换为可路由、可校验、可延迟执行的结构化意图计划。简单的单标签分类无法表达“查询历史订单后修改当前草稿”这类包含多个动作和数据依赖的请求，因此需要先独立建设意图规划子图。

## What Changes

- 新增主意图识别：区分 `order`、`qa` 和 `ambiguous`。
- 新增订单子意图多标签识别，支持 `create_order`、`modify_draft`、`query_history_order`。
- 将多个子意图组织为带稳定步骤 ID、顺序和依赖关系的 `IntentPlan`。
- 支持前一步结果被后一步引用的顺序依赖表达。
- 对缺少关键信息、低置信度或无法建立合法计划的请求标记澄清状态。
- 本阶段只识别和输出计划，不查询数据库、不修改草稿、不创建订单、不调用业务工具。

## Capabilities

### New Capabilities

- `intent-planning`: 将用户消息识别为主意图及多子意图计划的能力。

### Modified Capabilities

无。

## Impact

- 新增意图识别状态、子意图模型、IntentPlan 输出结构及 LangGraph 子图编排。
- 依赖现有 Python LLM 客户端调用能力，但不改变其接口。
- 后续主图、订单图和问答图将消费该计划；本 change 不实现这些下游图。
