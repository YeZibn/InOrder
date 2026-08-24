## MODIFIED Requirements

### Requirement: Provide an intent recognition graph

系统 SHALL 提供可独立调用且可作为 MainGraph 子图挂载的意图识别图；图输出至少包含 `main_intent` 和经过校验的 `intent_plan`，不得执行订单业务。

#### Scenario: Parent graph consumes intent output
- **WHEN** MainGraph 调用意图图
- **THEN** 意图图输出可供父图路由的 `main_intent` 和 `intent_plan`

#### Scenario: Intent graph remains recognition-only
- **WHEN** 意图图独立或被父图调用
- **THEN** 意图图只执行主意图、子意图和计划校验，不查询或修改真实订单
