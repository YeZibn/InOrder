## Purpose

为未能确定用户车型的订单提供可复现、可解释的确定性车型估算，使用车型主数据和多货物整体箱的简化极点装载计算，最多返回三个真实可行的候选车型。

## ADDED Requirements

### Requirement: Estimate vehicles deterministically

系统 SHALL 在用户未提供车型或车型表达无法唯一匹配时，仅依据货物画像、车辆特殊规格和集中车型主数据进行确定性车型筛选，不调用 LLM 选择车型。

#### Scenario: Estimate without user vehicle
- **WHEN** 当前订单没有可用的用户车型
- **THEN** 系统读取 `vehicles.json` 和完整货物画像计算车型候选，结果来源为 `estimated`

### Requirement: Support multiple cargo boxes in simplified extreme-point fitting

系统 SHALL 将每条货物画像的 `dimensions_cm` 视为一个独立整体长方体，先使用总重量和总体积快速过滤，再对每个货物依次尝试六种旋转方向和可用极点；放置不得超出车型边界或与已放置货物重叠。

#### Scenario: Fit different cargo sizes separately
- **WHEN** 订单包含苹果和冰箱两条不同尺寸的货物画像
- **THEN** 系统分别使用两条画像的长宽高参与装载计算，不将它们合并成一个总体尺寸

#### Scenario: Reject overlapping or out-of-bounds placement
- **WHEN** 某车型无法在其最大长宽高边界内放置全部货物，或任一货物与已放置货物重叠
- **THEN** 该车型不进入可行候选列表

### Requirement: Return at most three feasible candidates

车型估算 SHALL 只返回通过重量、总体积、特殊规格和简化极点装载计算的车型，按最小满足容量和剩余空间排序，最多返回三个；可行车型不足三个时不得用不可行车型补足。

#### Scenario: Return three candidates
- **WHEN** 至少三个车型通过全部确定性计算
- **THEN** 结果按适配度返回三个车型候选

#### Scenario: Return fewer than three candidates
- **WHEN** 只有一个或两个车型通过全部计算
- **THEN** 结果只返回实际通过的车型数量

#### Scenario: Return no candidate
- **WHEN** 没有车型通过全部计算
- **THEN** 返回空候选列表和可解释的失败原因

### Requirement: Preserve matched user vehicle priority

用户车型表达成功匹配主数据时，系统 SHALL 直接返回一个 `user_matched` 结果，不执行确定性估算，也不返回其他候选车型替换用户选择。

#### Scenario: Matched user vehicle bypasses estimation
- **WHEN** 用户输入“4米2”且匹配到 `truck_4m2`
- **THEN** 结果只包含 `truck_4m2`，来源为 `user_matched`
