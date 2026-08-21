## Context

当前项目已有确定性车型/规格关键词和精确匹配接口，并已建立 500 条明确写出的评估集。中文车型词通常很短，误归一代价高，生产链路必须优先 precision 和低 false-positive rate，而不是盲目追求召回率。

## Goals / Non-Goals

**Goals:**

- 保留可重复运行的 500 条正负样本集和评估输出。
- 将保守 Ensemble 作为生产唯一模糊匹配入口。
- 统一样本清洗、实体类型过滤、数字冲突和排除语义规则。
- 将高置信度归一结果写入 OrderContext，未接受结果进入上层澄清/待处理分支。

**Non-Goals:**

- 不修改现有 `vehicle-keyword-catalog` 的 canonical code 和精确匹配语义。
- 不实现 LLM/Embedding、范围求解、历史指代或车型推荐。

## Decisions

1. **精确优先、模糊后置。** 先调用现有精确 `find_vehicle_keyword`；只有精确匹配失败时才进入 Ensemble。精确结果不受模糊阈值影响。

2. **严格 Ensemble。** RapidFuzz 使用整体字符串相似度；n-gram 使用字符 bigram/trigram；生产策略要求两者返回相同 entity type 和 canonical code，并同时通过阈值、候选差距和业务规则。

3. **保守接受。** 短于 3 个字符、长度/数字不一致、范围、近似、比较、历史指代和混合实体表达直接拒绝。

4. **按实体类型隔离候选。** `vehicle_type` 与 `vehicle_specs` 不混合候选。

5. **生产写入边界。** 归一化层只返回 canonical code、原始输入、匹配方式和接受状态；只有 `accepted=true` 的结果才允许由现有 reducer 写入 `OrderContext.vehicle_type` 或 `OrderContext.vehicle_specs`。拒绝结果不覆盖已有上下文。

6. **依赖正式化。** RapidFuzz 固定进入项目运行依赖，避免生产环境与实验环境行为不一致。

## Risks / Trade-offs

- Ensemble 过于保守会降低 coverage，但优先避免错误车型写入；低置信度输入交给澄清。
- 生产环境缺少 RapidFuzz 会导致链路不可用，因此必须纳入正式依赖并在测试阶段验证安装。

## Migration Plan

新增归一适配器、依赖和测试，不需要迁移历史生产数据。现有精确匹配保持不变；模糊匹配仅对新进入归一化链路的值生效，拒绝时不覆盖已有 OrderContext。
