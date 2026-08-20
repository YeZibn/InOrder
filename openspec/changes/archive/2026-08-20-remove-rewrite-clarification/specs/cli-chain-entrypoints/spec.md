## MODIFIED Requirements

### Requirement: Order chain reports semantic parsing

CLI 的订单链路 SHALL 展示 rewrite 和 extract 的执行结果，不再展示 rewrite 澄清状态、澄清原因或“Extract 已跳过”。订单链路无论语义是否存在歧义，只要 rewrite JSON 合法，都应继续展示实体提取结果。

#### Scenario: Order chain displays best-effort extraction

- **WHEN** order 链路处理一个 rewrite 可以解析但指代不明确的用户输入
- **THEN** CLI SHALL 展示 Rewrite 已完成、Extract 已执行及实体数量，不展示澄清状态
