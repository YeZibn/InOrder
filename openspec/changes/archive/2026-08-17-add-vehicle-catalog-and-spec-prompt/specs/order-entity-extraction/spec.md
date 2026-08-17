## MODIFIED Requirements

### Requirement: Order entity extraction

系统 SHALL 在提取车型相关实体时区分基础车型/车长与车辆规格：基础车型和车长使用 `vehicle_type`，冷链、厢式、高栏、平板、危险品、高顶和尾板使用 `vehicle_specs`；同一输入中的基础车型和多个规格应分别输出实体，不得把车辆规格归为 `vehicle_type`。

#### Scenario: Extract cold-chain spec

- **WHEN** 用户说“要冷链车”
- **THEN** 系统输出 `vehicle_specs` 实体，规范值为 `cold_chain`，不输出具体 `vehicle_type`

#### Scenario: Extract combined vehicle and specs

- **WHEN** 用户说“要一辆4米2冷链厢式车”
- **THEN** 系统分别输出 `vehicle_type=truck_4m2`、`vehicle_specs=cold_chain` 和 `vehicle_specs=enclosed`

#### Scenario: Extract multiple vehicle specs separately

- **WHEN** 用户说“4米2高顶带尾板”
- **THEN** 系统输出一个车长实体和两个独立的 `vehicle_specs` 实体
