## ADDED Requirements

### Requirement: Use one order result shape across order and full chains

CLI 的 order 和 full 链路 SHALL 使用一致的 `order_result` 结构返回订单处理结果。订单上下文 SHALL 只通过 `order_result.order_context` 暴露；CLI SHALL 从该位置读取并保存成功返回的上下文，不得依赖根级订单字段作为兼容来源。

#### Scenario: Return an order result from the standalone order chain
- **WHEN** order 链路成功完成订单处理
- **THEN** Runner 在 `order_result` 下返回实体、订单上下文、车型解析和订单摘要等订单结果

#### Scenario: Return an order result from the full chain
- **WHEN** full 链路识别为订单并完成订单子图
- **THEN** Runner 返回 `intent_result` 与结构一致的 `order_result`，且订单上下文仅存在于 `order_result.order_context`

#### Scenario: Save the same context path in both chains
- **WHEN** order 或 full 链路成功返回最终 `order_result.order_context`
- **THEN** CLI 将该上下文保存为当前会话订单状态，供下一轮使用

#### Scenario: Do not save a context after failure
- **WHEN** order 或 full 链路执行失败且没有成功的 `order_result`
- **THEN** CLI 保留原会话订单上下文，不从部分状态更新它
