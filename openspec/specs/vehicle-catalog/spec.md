# vehicle-catalog Specification

## Purpose

为订单车型和车辆规格提供集中、稳定且可供 extract prompt 引用的领域词汇，避免基础车型与车辆能力混用。

## Requirements

### Requirement: Provide vehicle type catalog

系统 SHALL 提供基础车型和标准车长的稳定 code、label、category、别名及状态信息，并提供可序列化的长宽高、载货体积和载重范围。

#### Scenario: Catalog base vehicle types

- **WHEN** 查询车型主数据
- **THEN** 结果包含四轮小件、微面、小面、中面、大面、依维柯、微货、小货和中货及其稳定 code
- **THEN** 结果同时包含每条基础车型的能力范围字段

#### Scenario: Catalog length vehicle types

- **WHEN** 查询车长车型
- **THEN** 结果包含 3米8、4米2、5米2、6米2、6米8、7米6、8米2、8米6、9米6、11米7、12米5、13米、13米7、15米、16米和17米5，并提供长度信息

### Requirement: Provide vehicle specs catalog

系统 SHALL 提供冷链、厢式、高栏、平板、危险品、高顶和尾板等车辆规格的稳定 code、label、group、别名及状态信息。

#### Scenario: Catalog vehicle specs

- **WHEN** 查询车辆规格主数据
- **THEN** 结果包含 `cold_chain`、`enclosed`、`high_rail`、`flatbed`、`dangerous_goods`、`high_roof` 和 `tail_lift`

### Requirement: Keep catalog separate from extraction execution

车型主数据 SHALL 作为词汇和契约来源提供，但本次不要求根据目录执行实体归一化、模糊指代解析或选车决策。

#### Scenario: Catalog does not infer ambiguous vehicle

- **WHEN** 用户输入“之前那个车”或“小车”
- **THEN** 主数据不自动选择车型，交由后续澄清流程处理

### Requirement: Use one vehicle data source

车型目录 SHALL 通过统一 Provider 读取全国默认车型、城市覆盖和特殊规格；不得在其他代码文件中维护可导致不一致的完整车型记录。现有查询接口和 canonical code SHALL 保持兼容，本地车型表仅作为本地测试及远程服务不可用时的全国默认快照。

#### Scenario: Update a vehicle record
- **WHEN** 修改集中主数据表中的车型能力
- **THEN** catalog 查询返回更新后的能力，且无需同步修改另一份车型表

#### Scenario: Preserve lookup compatibility
- **WHEN** 查询“4.2米”“面包车”或“冷藏车”
- **THEN** 返回既有对应的 canonical code 和实体类型

#### Scenario: Share a city-aware provider
- **WHEN** 城市车型能力发生变化
- **THEN** 所有车型相关模块通过统一 Provider 获得同一版本的数据
