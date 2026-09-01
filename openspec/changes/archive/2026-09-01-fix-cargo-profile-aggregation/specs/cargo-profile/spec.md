## MODIFIED Requirements

### Requirement: Generate cargo constraint profiles

系统 SHALL 基于当前完整的原始货物记录调用 LLM 生成货物画像；画像 SHALL 按货物名称对应每种货物，并不得覆盖或改写原始 `cargo` 记录。原始货物记录中同一货物的重量、数量、体积和尺寸数组 SHALL 被解释为该货物多次新增或多条明细的累加记录，而不是候选值、替代值或仅取最后一项。

#### Scenario: Profile cargo with raw attributes

- **WHEN** 当前货物包含 `name=香蕉`、`weight=["1吨"]` 且其他原始属性为空
- **THEN** 系统返回香蕉画像，并保留原始货物记录不变

#### Scenario: Profile multiple cargo types

- **WHEN** 当前上下文包含苹果和香蕉两种货物
- **THEN** 系统分别返回两条画像，不将不同货物合并为一条画像

#### Scenario: Aggregate repeated raw cargo attributes

- **WHEN** 当前上下文包含 `name=苹果`、`weight=["1吨", "1吨"]`
- **THEN** 系统 SHALL 将两条重量记录均换算并累加，生成 `weight_kg=2000` 的苹果画像，不得只使用一条记录或将其视为候选值

### Requirement: Summarize cargo totals

系统 SHALL 返回当前所有货物的 `total_weight_kg` 和 `total_volume_m3` 汇总；汇总字段 SHALL 使用与画像相同的直接数值表达，不再附带 `weight_status`、`volume_status` 或字段级来源元数据。对每种货物，画像数值 SHALL 先汇总其全部原始累加记录；总汇总 SHALL 等于所有货物画像数值的合计。若任一货物核心数值无法估算，对应汇总值 SHALL 为 `null`，并通过各货物的 `reason` 体现原因。

#### Scenario: Summarize complete estimates

- **WHEN** 当前所有货物均有可用总重量和总体积
- **THEN** 系统 SHALL 返回具体的 `total_weight_kg` 和 `total_volume_m3`，且分别等于所有货物画像对应字段之和

#### Scenario: Partial total remains unavailable

- **WHEN** 至少一种货物的重量或体积完全无法估算
- **THEN** 对应汇总字段 SHALL 返回 `null`，不得生成无依据的替代数值

#### Scenario: Summarize repeated additions once

- **WHEN** 苹果原始重量为 `["1吨", "1吨"]`，且画像均可估算
- **THEN** `total_weight_kg` SHALL 为 `2000`，且不得再次叠加旧画像中的重量

### Requirement: Replace derived profile atomically

货物画像 SHALL 被视为基于当前完整 `cargo` 的派生数据；当原始货物发生新增、替换或删除时，系统 SHALL 基于完整货物集合重新生成并整体替换画像及汇总，不得按旧画像做增量拼接。原始 `cargo` SHALL 始终保留用户输入的原始表达，画像重建不得将归一化数值写回原始记录。

#### Scenario: Rebuild after cargo addition

- **WHEN** 已有苹果画像且原始货物新增一条苹果重量
- **THEN** 系统重新生成苹果画像和汇总，不重复累加旧画像结果

#### Scenario: Preserve raw records while replacing profiles

- **WHEN** 原始货物从 `weight=["1吨"]` 变为 `weight=["1吨", "500公斤"]`
- **THEN** 系统 SHALL 保留这两个原始表达，并以完整列表重新生成画像；旧画像不得作为新的输入或累加来源
