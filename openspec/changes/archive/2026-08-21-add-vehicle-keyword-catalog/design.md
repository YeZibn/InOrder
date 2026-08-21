## Context

当前 `catalog/vehicles.py` 已有基础车型、标准车长和车辆规格的 code、label、aliases，但 aliases 同时承担展示词汇和确定性匹配，且没有明确排除模糊词的契约。新的关键词 catalog 需要作为后续 normalization 的单一数据来源，并保持 Extract 的原文输出边界。

## Goals / Non-Goals

**Goals:**

- 建立 32 个确定性车型/规格 code 的关键词表。
- 保留 code、label、entity type、keywords 和 enabled 等稳定字段。
- 统一车长表达的无损格式清洗。
- 通过完整关键词校验避免模糊词进入确定性映射。

**Non-Goals:**

- 不实现 n-gram、TF-IDF、编辑距离或向量匹配。
- 不实现模糊候选、范围约束、历史指代解析或 LLM 判断。
- 不实现车型推荐、选车和货物边界校验。

## Decisions

1. **复用现有 catalog 数据结构并增加确定性关键词视图。** 保留已有 `VehicleType`/`VehicleSpec` 对外 API，通过稳定的 keyword record 或派生索引表达确定性映射，避免 prompt 和 normalization 各自维护表格。

2. **精确匹配优先。** 第一阶段只允许 canonical code、label 和声明过的关键词经过无损清洗后命中；未命中不进行猜测。

3. **车长使用专门的无损清洗。** 允许空格、全半角、`m`/`米` 和中文数字等格式变化；不解析“以上、左右、以内”等范围和近似语义。

4. **关键词唯一性是硬约束。** 同一实体类型下关键词不能映射多个 code；冲突数据应在测试或加载校验阶段暴露。

## Risks / Trade-offs

- [Risk] 关键词覆盖不足导致部分合法表达暂时无法归一 → 保留原文，后续根据真实样本增补表，不引入自动猜测。
- [Risk] 误把展示别名当成确定词 → 通过排除列表和唯一性测试控制，新增关键词需要明确业务确认。
- [Risk] 车长格式清洗过度 → 仅处理空格、字符形式和中文数字，不触碰范围/近似词。

## Migration Plan

先新增关键词数据和读取接口，再让后续车型 normalization 消费该接口。现有 `find_vehicle_type`/`find_vehicle_spec` 保持兼容；若发现关键词冲突，修正 catalog 数据后再启用归一，不涉及持久化迁移。
