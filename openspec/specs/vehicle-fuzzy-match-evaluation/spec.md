# vehicle-fuzzy-match-evaluation Specification

## Purpose

为中文车型短文本建立可复现的模糊匹配评估，并将通过评估的 RapidFuzz + 字符 n-gram 严格 Ensemble 接入生产车型归一化，在保持低误归一率的前提下处理高置信度变体。

## Requirements

### Requirement: Provide representative evaluation dataset

系统 SHALL 提供 500 条逐条写明、带期望结果和样本类别的车型匹配评估集，覆盖确定性关键词变体、明确不应匹配的模糊/范围/历史表达、短车型词和车长数字冲突。

#### Scenario: Evaluate positive variant
- **WHEN** 评估输入“4.2m”且期望 code 为 `truck_4m2`
- **THEN** 评估记录包含样本类别、期望 code 和可复现的匹配结果

#### Scenario: Evaluate negative expression
- **WHEN** 评估输入“小车”“4米以上”或“之前那个车”
- **THEN** 评估记录期望结果为空，不因算法给出候选就视为正确归一

### Requirement: Compare matcher strategies

系统 SHALL 分别评估 RapidFuzz、字符 bigram/trigram 和严格 Ensemble，并输出候选 code、分数、接受状态及匹配方法。

#### Scenario: Handle conflicting candidates
- **WHEN** RapidFuzz 和 n-gram 返回不同候选
- **THEN** Ensemble 不得自动归一，并标记为未接受

### Requirement: Enforce conservative acceptance rules

评估器和生产归一化 SHALL 支持实体类型过滤、最低分数、候选差距、输入长度、数字冲突和业务排除规则。

#### Scenario: Reject numeric conflict
- **WHEN** 输入为“4米3”而候选为 `truck_4m2`
- **THEN** 归一化拒绝该候选，即使字符串相似度达到普通阈值

### Requirement: Apply ensemble after exact matching

生产车型归一化 SHALL 先执行现有精确关键词匹配；仅在精确未命中时调用严格 Ensemble。只有两个 matcher 的 entity type 和 canonical code 一致且均通过规则时，才返回 `accepted=true`。

#### Scenario: Normalize after exact match misses
- **WHEN** 精确匹配未命中且输入为“4.2m”
- **THEN** Ensemble 返回 `truck_4m2`，并允许写入对应 OrderContext 字段

#### Scenario: Abstain on disagreement
- **WHEN** 两个 matcher 返回不同候选
- **THEN** 返回 `accepted=false`，不写入或覆盖 OrderContext

#### Scenario: Preserve context on unsafe input
- **WHEN** 输入为“4米以上”“之前那个车”或“4米3”
- **THEN** 拒绝自动匹配，并保留已有车型上下文不变

#### Scenario: Keep entity types isolated
- **WHEN** 输入属于 `vehicle_type` 或 `vehicle_specs`
- **THEN** 只在对应实体类型候选中匹配，不得跨类型归一

### Requirement: Report comparable metrics and preserve exact behavior

系统 SHALL 输出 precision、false-positive rate、coverage 和 abstain rate，并确保评估和模糊归一不改变现有精确 catalog 行为。

#### Scenario: Preserve exact canonical result
- **WHEN** 输入为现有精确关键词“4.2米”
- **THEN** 系统直接返回既有 `truck_4m2` canonical code，不调用模糊策略改变结果
