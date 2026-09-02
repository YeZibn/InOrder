## MODIFIED Requirements

### Requirement: Persist order context

系统 SHALL 持久化订单上下文中的装货地和卸货地，并保留地址的 `role`、可选 `province`、`city` 与 `full_address` 字段；未提供的字段 SHALL 保持为空，不得由上下文层推断或补全。

#### Scenario: Persist province when extracted
- **WHEN** location 实体包含 `province=浙江`、`city=温州` 和完整地址
- **THEN** OrderContext SHALL 原样保存这三个地址字段

#### Scenario: Preserve missing province
- **WHEN** location 仅包含 `city=温州`
- **THEN** OrderContext 的该地址 `province` SHALL 为空
