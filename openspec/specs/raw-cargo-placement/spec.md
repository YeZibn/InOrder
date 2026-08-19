# raw-cargo-placement Specification

## Purpose

为订单草稿提供一种不丢失用户原始货物描述的放置方式，在单位归一和智能估算完成前支持多轮增量输入，并为后续估算与车型选择保留可扩展的数据基础。

## Requirements

### Requirement: Preserve raw cargo attributes

系统 SHALL 将每条货物记录表示为货物名称以及原始属性值列表；支持的属性包括 `weight`、`quantity`、`volume` 和 `dimensions`。列表中的值 SHALL 保留用户或 rewrite 文本中的原始表达，不进行单位换算、数值计算或 LLM 推断。

#### Scenario: Place cargo from initial order

- **WHEN** 用户首次提供“一吨香蕉”
- **THEN** 当前货物记录包含 `name=香蕉`，且 `weight` 为 `["1吨"]`，其他未提供属性为空列表

#### Scenario: Preserve multiple raw weight expressions

- **WHEN** 同一货物先提供“一吨”并随后通过 `add` 提供“500公斤”
- **THEN** 该货物的 `weight` 为 `["1吨", "500公斤"]`，系统不计算总重量

#### Scenario: Preserve independent raw attributes

- **WHEN** 同一货物先提供“20箱”并随后提供“5立方”和“2米×1米×1米”
- **THEN** `quantity`、`volume` 和 `dimensions` 分别保存各自的原始值列表，互不拼接

### Requirement: Apply cargo actions without semantic inference

系统 SHALL 按货物名称识别同一货物并处理 action：`set`/`replace` 建立或替换该货物记录，`add` 追加非空属性，`remove` 移除该货物记录。系统不得根据字符串数字、单位或属性顺序推断业务含义。

#### Scenario: Replace cargo record

- **WHEN** 已有香蕉货物，用户以 `replace` 提供新的香蕉属性
- **THEN** 该货物的原始属性列表被新输入替换，不保留旧列表

#### Scenario: Remove cargo record

- **WHEN** 用户对香蕉货物执行 `remove`
- **THEN** 订单上下文中不再存在名称为香蕉的货物记录

#### Scenario: Ignore omitted attributes

- **WHEN** LLM 对本轮未提供的货物属性返回 `null` 或空值
- **THEN** 这些属性不进入列表，不触发拼接或合并错误

### Requirement: Keep raw placement extensible

系统 SHALL 保持货物原始属性结构可序列化，并允许后续在不改变原始列表语义的前提下增加单位归一结果、LLM 估算结果和车型选择结果。

#### Scenario: Serialize raw cargo context

- **WHEN** 当前订单上下文包含多条货物原始属性列表
- **THEN** 上下文可稳定转换为 JSON-compatible 数据，且所有原始表达保持可读
