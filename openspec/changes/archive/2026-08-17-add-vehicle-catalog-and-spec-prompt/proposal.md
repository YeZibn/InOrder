## Why

当前 extract prompt 将基础车型、车长和车辆规格混在一起，并把“冷链车”示例错误归为 `vehicle_type`。建立集中车型目录并修正 `vehicle_specs` 提取规则，可以先统一领域词汇，为后续车型归一化实现提供稳定事实来源。

## What Changes

- 新增静态车型主数据，覆盖基础车型和标准车长 code、label、category、别名及状态。
- 新增车辆规格主数据，覆盖冷链、厢式、高栏、平板、危险品、高顶和尾板。
- 修正 `EXTRACTION_SYSTEM_PROMPT`：明确基础车型/车长进入 `vehicle_type`，车辆能力、车厢、运输要求和装卸设备进入 `vehicle_specs`。
- 将冷链相关表达从 `vehicle_type` 示例调整为 `vehicle_specs`，并增加组合车型与规格的提取示例。
- 记录 prompt 变更。
- 暂不实现车型归一化执行器、reducer 分组替换、模糊指代消解、`X米以上`选择和选车逻辑。

## Capabilities

### New Capabilities

- `vehicle-catalog`: 提供基础车型与车辆规格的稳定主数据目录。

### Modified Capabilities

- `order-entity-extraction`: 修正 vehicle_type/vehicle_specs 的提取边界和冷链分类规则。

## Impact

影响新增车辆目录模块、extract prompt 与其测试及 prompt changelog；不新增外部依赖，不改变 reducer 或 LangGraph 结构。
