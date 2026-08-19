## Why

当前订单上下文直接保存货物属性的单个原始字符串，无法安全表达同一货物在多轮对话中的多次增量，例如“1吨”后再增加“500公斤”。在单位归一和货物估算尚未实现前，先保留每次用户提供的原始属性，避免错误计算和信息丢失。

## What Changes

- 按货物 `name` 聚合订单上下文中的同类货物。
- 将 `weight`、`quantity`、`volume` 和 `dimensions` 保存为原始值列表。
- 对 `add` 操作追加本轮非空属性值，不做单位换算、数值计算或语义推断。
- 对 `set`/`replace` 操作建立或替换该货物的原始属性列表。
- 将 `null` 视为本轮未提供的属性，不写入列表，也不参与合并。
- 保持 `remove` 按货物名称移除整条货物记录。

## Capabilities

### New Capabilities

- `raw-cargo-placement`: 保存和合并货物的原始属性值，为后续单位归一、货物估算和车型选择提供稳定输入。

### Modified Capabilities

- `conversation-order-context`: 修改货物 action reduction 的存储语义，从字符串覆盖/数值累加改为原始属性列表化保存。

## Impact

- 影响 `OrderContextReducer` 的货物合并逻辑及 `OrderContext.cargo` 的序列化结构。
- 需要更新订单上下文和订单处理子图的单元测试。
- 不新增依赖，不改变 LangGraph 拓扑，不修改 LangExtract 的实体语义契约。
- 后续单位归一、LLM 货物估算和车型选择可在该结构上独立扩展。
