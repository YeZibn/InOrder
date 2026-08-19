## Context

现有 `location` 实体通过 `role` 和 `city` 表达装货地、卸货地，`OrderContext` 的位置字段已经是 JSON-compatible mapping，因此可以在实体属性层扩展地址粒度而不改变上下文字段类型或 reducer 的 pickup/dropoff 路由。

## Goals / Non-Goals

**Goals:**

- 让 location 同时携带城市级 `city` 与用户明确说出的 `full_address`。
- 保留 grounded extraction 的原文边界，支持具体仓库、园区、门店等地址。
- 兼容仅有城市的旧输入与已有上下文序列化。

**Non-Goals:**

- 不拆分省、市、区、街道等行政层级。
- 不做地址标准化、地址库补全、地理编码、经纬度和路线计算。
- 不改变 location 的 pickup/dropoff role、action 或其他实体契约。

## Decisions

1. **采用两个业务字段**：只增加 `full_address`，与已有 `city` 组成两层地址模型，避免当前阶段引入过细的行政区字段。
2. **完整地址以原文为准**：`full_address` 保存本轮待提取文本中的连续地址表达；本地适配层只校验类型，不清洗、拼接或推断地址。
3. **城市字段保持保守**：LLM 仅在文本明确表达城市时输出 `city`；如果无法确定城市，`city` 为空或缺省，但 `full_address` 仍可保留。
4. **城市级输入向后兼容**：当用户只说城市时，`city` 保留城市名，`full_address` 可使用同一城市表达，以保证地址对象结构稳定。
5. **统一覆盖 JSON 与 LangExtract**：两种 extract backend 使用相同的 location attributes 契约和 few-shot 语义，避免 CLI 后端切换产生字段差异。

## Risks / Trade-offs

- [LLM 可能把过长句子当作完整地址] → 强调连续原文、地址边界和 few-shot，适配层仅做类型与来源校验。
- [用户地址缺少城市] → 保留 `full_address`，将 `city` 设为空/缺省，不进行本地补全。
- [旧 context 只有 city] → 新字段为可选且 mapping 兼容，旧上下文继续可读写。
- [不同 backend 输出字段不一致] → 为 JSON resolver 和 LangExtract adapter 增加相同契约测试。

## Migration Plan

1. 更新 order entity extraction 的 prompt、LangExtract 描述和示例。
2. 增加 city/full_address 的解析、grounded 边界和 reducer 兼容性测试。
3. 保持已有仅城市测试通过，逐步在 CLI 中观察详细地址提取结果。
4. 如需回滚，停止使用 `full_address` 字段即可，现有 `city` 和 role 语义保持可用。
