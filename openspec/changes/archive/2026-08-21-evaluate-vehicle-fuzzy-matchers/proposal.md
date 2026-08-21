## Why

确定性车型关键词表已经完成。现在需要将经过 500 条样本验证的 RapidFuzz + 字符 n-gram 严格 Ensemble 接入车型归一化链路，在精确匹配失败时安全处理轻微变体，同时对模糊输入保持拒绝。

## What Changes

- 保留 500 条明确写出的车型评估集和三种策略的离线回归报告。
- 将 RapidFuzz + 字符 bigram/trigram 的严格 Ensemble 作为正式生产匹配策略。
- 精确关键词匹配优先；仅在精确匹配失败后调用 Ensemble。
- 只有两个 matcher 候选一致、均通过阈值、候选差距和业务规则时才自动归一，否则返回未接受结果供上层澄清。
- 将归一结果安全写入车型对应的 OrderContext 字段，不改变 Extract 保留用户原文的行为。
- 将 RapidFuzz 纳入正式运行依赖，并保留 precision、false-positive rate、coverage、abstain rate 回归指标。

## Capabilities

### New Capabilities

- `vehicle-fuzzy-match-evaluation`: 车型模糊匹配评估与生产 Ensemble 归一化。

### Modified Capabilities

- 车型归一化链路：精确匹配失败后增加严格 Ensemble。

## Impact

- 扩展现有车型归一化模块和 OrderContext 更新链路。
- RapidFuzz 成为正式依赖；现有精确 catalog 和 Extract 原文输出保持兼容。
- 500 条评估集继续作为生产归一化的回归门禁和阈值依据。
