## MODIFIED Requirements

### Requirement: Support multiple cargo boxes in simplified extreme-point fitting

系统 SHALL 将每条货物画像的 `dimensions_cm` 视为一个独立整体长方体，先使用总重量和总体积进行必要条件筛选，再对每个货物依次尝试六种旋转方向和可用极点。车型估算 SHALL 分别将每项能力范围的下界和上界传入相同筛选及摆放计算；一次摆放结果只适用于对应边界。放置不得超出该边界或与已放置货物重叠。计算所需货物尺寸缺失时 SHALL NOT 跳过该货物并报告下界通过。

#### Scenario: Fit different cargo sizes separately
- **WHEN** 订单包含苹果和冰箱两条不同尺寸的货物画像
- **THEN** 系统分别使用两条画像的长宽高参与装载计算，不将它们合并成一个总体尺寸

#### Scenario: Evaluate each capacity boundary separately
- **WHEN** 某车型的能力包含上下界
- **THEN** 系统分别使用该车型的下界和上界进行重量、体积和摆放计算，不把不同边界的结果混成一次通过

#### Scenario: Reject overlapping or out-of-bounds placement
- **WHEN** 某次摆放超出当前评估边界或与已放置货物重叠
- **THEN** 该边界下的计算不得报告摆放通过

#### Scenario: Do not skip cargo with missing dimensions
- **WHEN** 任一货物缺少摆放计算所需的长、宽或高
- **THEN** 系统不得跳过该货物后将车型标记为 `lower_bound_fit`

### Requirement: Return at most three feasible candidates

车型估算 SHALL 分别按每项能力范围的下界和上界评估候选，并最多返回三个车型。通过全部下界检查的候选 SHALL 标记为 `lower_bound_fit`；未通过下界但通过全部上界检查的候选 SHALL 标记为 `upper_bound_only`，表示可能适配而非确认适配。候选 SHALL 先按等级排序，`lower_bound_fit` 优先于 `upper_bound_only`；每个等级内优先排列按对应边界计算时容量较小且够用的车型，并用稳定车型 code 作为最终排序依据。额外的统一预留比例不在本变更范围内。

#### Scenario: Prefer the smallest candidate that passes lower bounds
- **WHEN** 多个车型都通过全部能力下界检查
- **THEN** 容量较小且够用的 `lower_bound_fit` 车型 SHALL 排在该等级前面

#### Scenario: Include candidates that pass only upper bounds
- **WHEN** 某车型未通过全部能力下界检查，但通过全部能力上界检查
- **THEN** 该车型 SHALL 以 `upper_bound_only` 出现在推荐候选中，并排在所有 `lower_bound_fit` 候选之后

#### Scenario: Fill the shortlist with upper-bound candidates
- **WHEN** `lower_bound_fit` 候选少于三个且存在 `upper_bound_only` 候选
- **THEN** 系统 SHALL 在下界候选之后加入排序靠前的上界候选，直到最多三个

#### Scenario: Return fewer than three candidates
- **WHEN** 通过下界或上界计算的候选总数不足三个
- **THEN** 结果 SHALL 只返回实际候选数量

#### Scenario: Return no candidate
- **WHEN** 没有车型通过下界或上界计算
- **THEN** 系统 SHALL 返回空候选列表和可解释的失败原因
