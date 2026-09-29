## ADDED Requirements

### Requirement: Expose one order context in the finalized parent result

MainGraph SHALL 在父图内部保留完成子图编排所需的工作状态；对调用方返回的完整订单结果 SHALL 只在 `order_result.order_context` 暴露更新后的订单上下文，不得再提供根级重复的 `order_context`。QA 等未执行订单子图的路径 SHALL 不生成订单结果或订单上下文。

#### Scenario: Return one context after the order route
- **WHEN** MainGraph 路由到订单子图并成功完成
- **THEN** 完整结果在 `order_result.order_context` 提供最终上下文，且根级结果不包含第二份 `order_context`

#### Scenario: Do not return order context on the QA route
- **WHEN** MainGraph 将请求路由到 QA 终止分支
- **THEN** 结果不包含订单子图结果或订单上下文
