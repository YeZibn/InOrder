## Purpose

为订单车型和车辆规格提供集中、稳定且可供 extract prompt 引用的领域词汇，避免基础车型与车辆能力混用。

## ADDED Requirements

### Requirement: Provide vehicle type catalog

系统 SHALL 提供基础车型和标准车长的稳定 code、label、category、别名及状态信息。

#### Scenario: Catalog base vehicle types

- **WHEN** 查询车型主数据
- **THEN** 结果包含四轮小件、微面、小面、中面、大面、依维柯、微货、小货和中货及其稳定 code

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
