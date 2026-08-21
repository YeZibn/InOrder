## Purpose

为车型归一提供一份只包含高置信、可直接确定 canonical code 的关键词映射，统一基础车型、标准车长和车辆规格的词汇来源，并排除模糊表达。

## ADDED Requirements

### Requirement: Provide deterministic vehicle keyword mappings

系统 SHALL 提供基础车型、标准车长和车辆规格的确定性关键词映射。每条映射 SHALL 包含实体类型、canonical code、标准名称、关键词集合和启用状态；同一关键词在同一实体类型下 SHALL 只对应一个 code。

#### Scenario: Match base vehicle keyword
- **WHEN** 查询关键词“面包车”
- **THEN** 系统返回 `vehicle_type=medium_van`，且映射状态为启用

#### Scenario: Match standard length keyword
- **WHEN** 查询关键词“4.2米”或“四米二”
- **THEN** 系统返回 `vehicle_type=truck_4m2`

#### Scenario: Match vehicle specification keyword
- **WHEN** 查询关键词“冷藏车”或“带尾板”
- **THEN** 系统分别返回 `vehicle_specs=cold_chain` 或 `vehicle_specs=tail_lift`

### Requirement: Cover confirmed vehicle vocabulary

系统 SHALL 覆盖 9 个基础车型、16 个标准车长和 7 个车辆规格。标准车长关键词 SHALL 支持数字、带小数点、英文 m、中文数字等不改变语义的表达形式。

#### Scenario: Catalog contains confirmed base types
- **WHEN** 读取车型关键词 catalog
- **THEN** 结果包含四轮小件、微面、小面、中面、大面、依维柯、微货、小货和中货

#### Scenario: Catalog contains confirmed lengths
- **WHEN** 读取车型关键词 catalog
- **THEN** 结果包含 3米8、4米2、5米2、6米2、6米8、7米6、8米2、8米6、9米6、11米7、12米5、13米、13米7、15米、16米和17米5

#### Scenario: Catalog contains confirmed specifications
- **WHEN** 读取车型关键词 catalog
- **THEN** 结果包含冷链、厢式、高栏、平板、危险品、高顶和尾板

### Requirement: Normalize harmless textual variants

关键词匹配 SHALL 在不改变业务语义的范围内清洗空格、大小写、全半角，并将已约定的车长表达统一为可匹配形式，例如“4.2 米”“4 米 2”“4m2”和“四米二”。清洗不得把范围、近似或比较表达转换为具体车型。

#### Scenario: Normalize spacing and unit variants
- **WHEN** 输入“4.2 米”或“4 米 2”
- **THEN** 系统将其匹配到 `truck_4m2`

#### Scenario: Preserve non-specific length semantics
- **WHEN** 输入“4米左右”或“4米以上”
- **THEN** 系统不得返回任何具体标准车长 code

### Requirement: Exclude ambiguous and contextual expressions

确定性关键词 catalog SHALL 不包含无法唯一映射车型的通用词、模糊词、范围词、近似词或历史指代表达，例如“小车”“大车”“货车”“卡车”“面包”“4米左右”“4米以上”和“之前那个车”。未命中确定性关键词时，系统 SHALL 保留原文供后续流程处理，不得强制猜测 code。

#### Scenario: Do not map generic vehicle word
- **WHEN** 查询关键词“小车”或“货车”
- **THEN** 确定性 catalog 不返回具体车型 code

#### Scenario: Do not map historical reference
- **WHEN** 查询“之前那个车”
- **THEN** 确定性 catalog 不返回具体车型 code

### Requirement: Keep catalog as a single source of truth

系统 SHALL 通过统一 catalog 读取关键词映射，prompt、normalization 和测试不得各自维护另一份车型关键词表。关键词、label 和 code SHALL 可被稳定读取和序列化。

#### Scenario: Read stable keyword record
- **WHEN** 调用方读取任一已启用关键词记录
- **THEN** 结果包含实体类型、code、label、keywords 和 enabled 字段，且重复读取顺序稳定
