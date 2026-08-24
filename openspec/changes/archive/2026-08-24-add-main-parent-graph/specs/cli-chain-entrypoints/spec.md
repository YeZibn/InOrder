## MODIFIED Requirements

### Requirement: Route messages by selected chain

CLI SHALL 将普通消息路由到当前链路对应的图入口：`intent` 只调用意图子图，`order` 只调用订单处理子图，`full` 调用 MainGraph，由 MainGraph 编排意图子图并在主意图为 `order` 时继续调用订单处理子图。

#### Scenario: Full chain invokes parent graph
- **WHEN** 当前链路为 `full` 且用户输入普通消息
- **THEN** CLI 调用 MainGraph，不再由 CLI runner 手工顺序调用两个子图

#### Scenario: Intent chain remains direct
- **WHEN** 当前链路为 `intent`
- **THEN** CLI 直接调用意图子图并输出意图计划

#### Scenario: Order chain remains direct
- **WHEN** 当前链路为 `order`
- **THEN** CLI 直接调用订单处理子图并输出订单解析状态
