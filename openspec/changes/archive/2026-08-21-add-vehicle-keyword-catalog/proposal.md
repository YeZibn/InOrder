## Why

车型 catalog 目前主要保存 label、alias 和 code，但“哪些词可以直接确定车型”尚未形成独立契约。需要先建立一张仅包含高置信关键词的确定性映射表，作为后续车型归一和测试的单一事实来源，避免把“小车”“4米以上”等模糊表达误归一为具体车型。

## What Changes

- 为基础车型、标准车长和车辆规格建立确定性关键词映射表。
- 统一记录实体类型、canonical code、标准名称、关键词和启用状态。
- 纳入当前已确认的 9 个基础车型、16 个标准车长和 7 个车辆规格。
- 支持无语义变化的格式清洗，如空格、大小写、全半角和常见车长写法。
- 明确不纳入小车、大车、货车、卡车、面包、4米左右、4米以上及历史指代表达。
- 本 change 不实现 n-gram、TF-IDF、编辑距离、LLM 模糊判断、范围求解或车型推荐。

## Capabilities

### New Capabilities

- `vehicle-keyword-catalog`: 提供可直接确定车型或车辆规格的关键词映射契约。

### Modified Capabilities

无。

## Impact

- 扩展 `src/inorder_llm/catalog/vehicles.py` 或相关 catalog 模块的数据模型和读取接口。
- 后续 normalization 可直接消费该表生成 canonical code。
- 需要补充 catalog 数据完整性、关键词唯一性和模糊词排除测试。
- 不改变当前 Extract 的原文输出契约，也不改变订单图执行流程。
