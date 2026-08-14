## MODIFIED Requirements

### Requirement: Conditional main-intent routing

图 SHALL 根据主意图在 `order` 和 `qa` 两个分支之间路由；不得注册或执行 `ambiguous` 分支。

#### Scenario: Order enters sub-intent node
- **WHEN** 主意图节点输出 `order`
- **THEN** 图路由到子意图节点并继续构建订单意图计划

#### Scenario: QA bypasses sub-intent node
- **WHEN** 主意图节点输出 `qa`
- **THEN** 图不执行子意图节点并返回空订单子意图计划

### Requirement: Unified graph output

所有分支 SHALL 通过统一出口返回包含 `order` 或 `qa` 主意图、子意图计划和澄清状态的状态结构。

#### Scenario: Two branches share one output
- **WHEN** 图处理 order 或 qa 请求
- **THEN** 两条路径都通过统一出口返回相同字段结构
