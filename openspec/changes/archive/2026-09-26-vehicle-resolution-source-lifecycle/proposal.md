## Why

车型上下文同时承载用户选择和系统估算，但来源更新、估算失效和模糊替换的规则尚未形成一致契约。由此可能把仅补充车型规格误标成用户选车，或在新估算无主车型时继续保留过期车型；本 change 明确当前车型的唯一来源及跨轮次生命周期。

## What Changes

- 将 `OrderContext.vehicle_type` 定义为当前生效车型，并以 `vehicle_source` 严格标记其来源：仅成功匹配的用户车型可标为 `user_matched`，系统主车型标为 `estimated`，无生效车型时来源为空。
- 保持用户明确指定且匹配成功的车型优先：后续货物、城市或车型规格变化均不得触发货物适配校验、自动估算或替换该车型。
- 将用户车型规格与车型来源解耦；规格更新不改变 `vehicle_source`，并在车型解析结果中保留用户规格。现有车辆能力计算保持不变，不新增车型与规格的兼容性映射。
- 让货物画像、起点城市或用户车型规格变化使系统估算失效并重新计算；若没有下界通过的估算主车型，清除旧的 `estimated` 车型和来源，同时保留本轮候选与原因。
- 明确车型删除及无法匹配的新车型表达的动作语义：明确 remove 清除当前车型并进入估算；明确 replace 且新车型无法匹配时撤销旧车型、保留原始表达并进入估算；不带替换意图的模糊表达不得清除已有用户车型。
- 保留现有车型上下界计算、候选排序和 `OrderGraph` 拓扑，不新增并行的用户车型/推断车型字段。

## Capabilities

### New Capabilities

<!-- None. This change revises the existing vehicle-resolution contract. -->

### Modified Capabilities

- `vehicle-resolution-and-estimation`: 明确用户来源锁定、规格来源隔离、推断依赖失效、无主车型清理，以及 remove/无法匹配 replace 的跨轮行为。

## Impact

- 代码：`OrderContextReducer`、`ContextUpdateNode`、`VehicleResolutionNode`、车型解析协议与 resolver 输入，以及相关单元测试。
- 数据契约：不新增 `OrderContext` 字段；明确 `vehicle_specs` 保存用户规格，货物画像推导的规格仅存在于车型决策结果中。
- OpenSpec：更新 `vehicle-resolution-and-estimation` 的主行为规格；不改变目录能力、货物装载算法或推荐排序规则。
