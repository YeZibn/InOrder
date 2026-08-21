## Purpose

为车型识别、规格归一和后续车辆可行性判断提供一份集中、稳定、可序列化的车型主数据表，避免不同模块重复维护相互矛盾的车型记录。

## Requirements

### Requirement: Provide a single vehicle master table

系统 SHALL 在独立的数据目录中提供车型主数据表，并为每条基础车型记录稳定的 `code`、`label`、`category`、`aliases`、车身长宽高范围、载货体积范围和载重范围；数据 SHALL 可被稳定读取和序列化。

#### Scenario: Read a standard length vehicle
- **WHEN** 调用方读取 `truck_5m2`
- **THEN** 返回 5米2 的别名以及长度、宽度、高度、体积和载重范围，且字段单位由字段名明确表达

#### Scenario: Read compact vehicle records
- **WHEN** 调用方读取小面、中面、微货或小厢货
- **THEN** 返回对应基础车型的 canonical code、关键词和完整能力范围

### Requirement: Cover the confirmed vehicle set

主数据表 SHALL 覆盖已确认的基础车型和标准车长：小面、中面、微货、小平板、小厢货、小高栏、依维柯、小货，以及 3米8、4米2、5米2、6米2、6米8、7米6、8米2、8米6、9米6、11米7、12米5、13米、13米7、15米、16米和17米5。

#### Scenario: Enumerate standard lengths
- **WHEN** 枚举车型主数据
- **THEN** 每个确认的标准车长恰好有一个 canonical code，且不会因重复旧表产生重复记录

### Requirement: Store special specifications separately

主数据表 SHALL 将 `cold_chain`、`enclosed`、`high_rail`、`flatbed`、`dangerous_goods`、`high_roof` 和 `tail_lift` 作为独立特殊规格记录，包含稳定 code、label、group 和 aliases；特殊规格不得重复出现在基础车型记录中。

#### Scenario: Combine a vehicle type with cold chain
- **WHEN** 调用方读取车型 `truck_5m2` 并附加 `cold_chain`
- **THEN** 系统可分别取得基础车型能力和冷链规格，不把冷链误当作另一种基础车型

### Requirement: Remove duplicate legacy data sources

迁移完成后，系统 SHALL 只从新的车型主数据表读取车型记录；旧的重复车型表文件或重复常量 SHALL 被删除或不再参与运行时加载，查询 API、canonical code 和既有关键词匹配行为 SHALL 保持兼容。

#### Scenario: Query through the existing catalog API
- **WHEN** 现有调用方查询“4.2米”“面包车”或“冷藏车”
- **THEN** 返回结果与迁移前相同，但记录来自新的唯一主数据表

#### Scenario: Prevent a second source of truth
- **WHEN** 新增车型或修改车型能力
- **THEN** 只需修改主数据表即可，代码和测试不得再维护另一份完整车型记录
