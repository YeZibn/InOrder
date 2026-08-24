## Why

当前车型估算仍依赖 LLM 选择车型，但车型能力和候选排序已经由固定车型主数据定义，LLM 会引入不稳定且不可复现的选择结果。需要改为纯确定性计算，并在多种货物同时存在时使用简化的极点装载计算，最终返回最多三个真实可装载的车型候选。

## What Changes

- 移除车型估算阶段的 LLM 选车逻辑，改为读取 `vehicles.json` 并执行确定性车型筛选。
- 用户车型表达匹配 JSON 成功时直接采用用户车型，不进入估算计算。
- 用户未提供车型或匹配失败时，先按重量、总体积和特殊规格做快速筛选，再进行多货物整体箱的简化极点计算。
- 每种货物画像作为一个独立整体长方体，支持六种旋转方向和基本不重叠/边界判断。
- 按适配度排序，最多返回三个可行车型；少于三个时不补充不可行车型。
- 保持 cargo profile LLM 只负责货物画像，不负责车型选择。

## Capabilities

### New Capabilities

- `vehicle-rule-based-extreme-point-estimation`: 使用车型主数据和简化极点算法确定性估算最多三个车型候选。

### Modified Capabilities

- `vehicle-resolution-and-estimation`: 将估算实现从 LLM 选择改为确定性计算，并支持最多三个候选。
- `order-processing-subgraph`: 更新订单图中的车型估算结果形态和来源行为。

## Impact

- 影响 `src/inorder_llm/vehicle_resolution/`、订单 LangGraph 状态和 CLI 输出。
- 继续使用现有 `vehicles.json`、车型关键词匹配和 `CargoProfile` 字段。
- 移除车型估算对 LLM client 的运行时依赖，但不影响 rewrite、extract 和 cargo profile 的 LLM 调用。
