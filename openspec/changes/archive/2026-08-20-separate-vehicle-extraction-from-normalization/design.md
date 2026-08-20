## Context

当前 `extract` 使用 LangExtract grounded extraction，但车型 prompt 同时承担了词汇说明和 canonical code 生成，且车型 catalog、prompt 示例和后续上下文写入之间没有单一边界。订单图在 extract 后直接更新内存 `OrderContext`，因此本 change 必须先固定实体的原文契约，并明确后续归一模块的输入。

## Goals / Non-Goals

**Goals:**

- 让车型和车辆规格提取结果可追溯到用户本轮文本。
- 使用 catalog 统一生成车型提示词中的词汇和分类信息。
- 保留基础车型/车长与车辆规格的拆分能力。
- 为后续确定性车型归一提供稳定的 `extraction_text`/原始表达输入。

**Non-Goals:**

- 不实现车型归一、模糊匹配、TF-IDF、范围约束求解或车型推荐。
- 不实现货物画像、装箱算法或车型与货物的边界校验。
- 不改变历史订单查询、订单创建和确认流程。

## Decisions

1. **Extract 保留原文，归一后置。** `vehicle_type` 和 `vehicle_specs` 的 `extraction_text` 是原始证据；LLM 不负责最终 code。这样可以避免模型幻觉 code，并允许以后替换归一算法而不重做提取。

2. **Catalog 是唯一词汇来源。** prompt 展示内容从 `catalog/vehicles.py` 动态构建；adapter 和 extract prompt 不再各自维护完整 code/别名列表。catalog 可用于分类提示，但不在本 change 内执行匹配。

3. **模糊表达进入后续阶段。** “小车”“4米左右”“9米以上”“之前那个车”等表达可以被提取，但不得在 extract 阶段被强制映射到具体 code。范围和指代信息作为原文或属性保留。

4. **不采用 TF-IDF 作为 extract 逻辑。** 相似度算法属于后续车型归一的候选生成问题；在本 change 中不引入算法依赖，也不把相似度结果写入实体。

5. **兼容现有实体模型。** 优先复用 `Entity.extraction_text` 和 `attributes`，不新增强制字段；若需要保留原始值，使用可选的 `raw` 属性，避免破坏其他实体类别。

## Risks / Trade-offs

- [Risk] 现有 reducer 可能把未归一车型原文直接写入 `OrderContext.vehicle_type` → 在实现测试中明确验证 extract 契约，并为后续车型归一预留边界；本 change 不把模糊原文当成合法 canonical code。
- [Risk] 动态 prompt 内容过长或目录变更影响模型输出 → 保持 catalog 展示紧凑，只呈现 label、alias 和类别，不把业务推荐规则放入 prompt。
- [Risk] 旧测试断言 code 直接来自 extract → 更新测试为断言原文保留和实体拆分；车型 code 的断言迁移到未来 normalizer change。

## Migration Plan

先更新 prompt、catalog 展示接口、LangExtract examples 和解析测试，再运行现有测试集。若需要回滚，恢复旧 prompt 和 examples 即可；catalog 数据结构保持向后兼容，不涉及持久化迁移。
