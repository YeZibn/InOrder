## MODIFIED Requirements

### Requirement: Use one vehicle data source

车型目录 SHALL 通过统一 Provider 读取全国默认车型、城市覆盖和特殊规格；extract、归一化、上下文更新及车型估算不得各自维护完整车型记录。现有查询接口和 canonical code SHALL 保持兼容，本地车型表仅作为本地测试及远程服务不可用时的全国默认快照。

#### Scenario: Share a city-aware provider
- **WHEN** 城市车型能力发生变化
- **THEN** 所有车型相关模块通过统一 Provider 获得同一版本的数据

#### Scenario: Preserve lookup compatibility
- **WHEN** 查询“4.2米”“面包车”或“冷藏车”
- **THEN** Provider 返回既有对应的 canonical code 和实体类型
