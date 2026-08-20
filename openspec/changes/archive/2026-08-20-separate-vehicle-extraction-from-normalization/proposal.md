## Why

当前订单 extract prompt 要求 LLM 直接生成车型 code，导致原文识别、车型归一和模糊判断混在一起，容易产生不存在的 code、错误的车型选择，也使车型表与 prompt 重复维护。需要先固定 extract 的原文证据边界，为后续独立车型归一模块提供稳定输入。

## What Changes

- 将车型表作为 extract 的动态词汇和实体分类来源，避免在 prompt 中重复维护车型清单。
- `vehicle_type` 和 `vehicle_specs` 提取时保留用户原文，不要求 LLM 生成最终 canonical code。
- 保持基础车型/车长与车辆规格的拆分规则，组合表达拆成多个实体。
- 为模糊、范围和历史指代表达定义 extract 输出边界；extract 不替用户选择具体车型。
- 调整实体提取的 few-shot、解析校验和相关测试契约。
- **BREAKING**：车型 code 的生成从 extract prompt 移出，交由后续车型归一模块负责；本 change 不实现该归一模块。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `order-entity-extraction`: 修改车型实体的 attributes 契约、车型表引用方式和原文保留规则。

## Impact

- 影响 `src/inorder_llm/extract/resolver.py`、LangExtract examples、实体解析测试及车型 catalog 的 prompt 展示接口。
- 后续 `vehicle_normalization` 模块将依赖本 change 产出的 `extraction_text`/原始表达；本 change 不改变车型选择、订单推荐或装箱逻辑。
- 需要处理现有 reducer 对车型值的兼容边界，避免未归一原文被误当作 canonical code。
