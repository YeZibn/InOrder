## Why

车型估算目前使用每项能力范围的上界判断候选，并将上界通过的车型作为普通可行车型返回。对每项范围分别计算上下界，可以优先推荐按保守边界仍够用的较小车型，同时保留仅上界通过的车型供用户参考。

## What Changes

- 对每个车型分别按载重、体积及货厢长宽高的下界和上界执行现有筛选与摆放计算。
- 将下界通过的候选排在前面；仅上界通过的候选仍可进入最多三个推荐项，但标明“可能适配”并排在下界候选之后。
- 在同一适配等级内优先选择容量较小且够用的车型；不得用上界通过的候选伪装成下界通过。
- 只有下界通过的估算车型可以成为主车型并写入订单上下文。用户明确指定的车型保持不变。
- 若货物缺少装载计算所需的尺寸，不得跳过该货物后报告下界通过。
- 沿用现有车型范围和极点摆放算法；不新增车型目录字段、RPC 契约或额外预留比例。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `vehicle-rule-based-extreme-point-estimation`: 分别评估能力下界和上界，并按下界候选优先、上界候选次之返回最多三个车型。
- `vehicle-resolution-and-estimation`: 返回有等级的候选；仅下界通过候选成为估算主车型。
- `order-processing-subgraph`: 只将下界通过的估算主车型写入订单上下文。

## Impact

- 影响 `src/inorder_llm/vehicle_resolution/`、`src/inorder_llm/graph/order/` 和 CLI 的车型结果呈现，以及对应测试。
- 候选结果以适配等级区分下界通过和仅上界通过；不再用无等级的 `fit=true` 表示两者。
- 不改 `vehicles.json`、目录 Provider/RPC、车型范围数据或现有摆放策略，也不声称估算结果构成真实车辆的装载认证。
