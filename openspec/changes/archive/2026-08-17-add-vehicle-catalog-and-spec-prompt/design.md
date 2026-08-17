## Context

当前 extract prompt 已定义 `vehicle_type` 和 `vehicle_specs`，但车型列表混合了基础车型、车长和规格，且冷链示例被归到了 `vehicle_type`。本 change 只建立主数据并修正 prompt 分类，不实现归一化执行器。

## Goals / Non-Goals

**Goals:**

- 建立可被后续代码和 prompt 复用的车型与规格目录。
- 将冷链、厢式、高栏、平板、危险品、高顶、尾板明确归入 `vehicle_specs`。
- 修正 prompt 示例和组合提取规则。

**Non-Goals:**

- 不新增车型归一化函数或修改 reducer。
- 不处理模糊车型、历史指代、`X米以上`约束和选车决策。
- 不推断载重、体积或车型能力。

## Decisions

### 使用两个静态目录

新增 `vehicle_type` 目录和 `vehicle_specs` 目录。车型记录至少包含 code、label、category、aliases、status；车长车型额外包含 length_cm；规格记录包含 code、label、group、aliases、status。静态目录不引入外部依赖，便于测试和审查。

### 规格独立于基础车型

“4米2冷链车”由一个基础车型和一个规格组成，而不是创建 `cold_chain_4m2` 组合车型。这样避免组合数量膨胀，并与现有 `OrderContext.vehicle_type`/`vehicle_specs` 字段保持一致。

### Prompt 使用目录 code

extract 的 `vehicle_type` 和 `vehicle_specs` 示例使用目录 code 作为 `attributes.value`，同时保留 `extraction_text` 原文。Prompt 负责分类与提取，不负责解决指代或根据货物选择车型。

### 兼容旧实体范围

保留现有基础车型列表和明确别名；仅修正冷链示例及新增规格分类规则。本次不删除已有实体类型，避免影响现有解析测试。

## Risks / Trade-offs

- [业务车型标准未完全确定] → 目录只收录当前已确认词汇，不建立微面/小面或货车类别之间的推导关系。
- [Prompt 输出 code 仍可能不稳定] → 本次增加 prompt 断言测试；真正的代码归一化另行实施。
- [规格分组未来变化] → 记录 group 字段但不在本次实现分组替换逻辑。
