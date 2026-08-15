## Context

现有 `extract.Entity` 已包含 `type`、`action`、`attributes` 和 `extraction_text`，但没有承载跨轮状态的领域对象。当前图 state 只描述一次意图识别执行，CLI session 也只保存原始字符串列表。

## Goals / Non-Goals

**Goals:**

- 建立 `context/` 包，分离会话历史、订单草稿和状态合并逻辑。
- 让 reducer 对每种 action 有确定、可单测的行为。
- 仅支持一个 active order context，并提供 JSON-compatible 序列化。
- 保持 EntityExtractor、IntentGraph 和 CLI 现有行为不变。

**Non-Goals:**

- 不引入数据库、checkpoint、历史订单 API 或多草稿切换。
- 不把 context 自动接入 LangGraph 或 CLI；后续 change 再做集成。
- 不执行任何订单业务操作。

## Decisions

### 分离 history 与 order context

`HistoryConversation` 只保存对话回合，`OrderContext` 只保存当前订单字段，`ConversationSession` 负责组合。相比一个大而扁平的状态对象，这能避免对话文本和业务字段相互污染。

### Reducer 作为唯一修改入口

`OrderContextReducer` 接收 immutable `Entity` 列表并更新 context。提取器不直接改状态，便于回放、审计和测试。

### 字段策略

地址、联系人、车型、时间、支付等单值字段使用 set/replace 覆盖；cargo 作为列表按货物名称匹配，add 合并数量/重量，remove 删除匹配货物；vehicle_specs 与 remark 的 list/string 行为在 reducer 中集中定义。

### 保守合并

无法从 entity attributes 得到可靠的数字或匹配键时，不猜测转换规则；保留实体信息或抛出明确的领域错误，由上层决定是否澄清。

## Risks / Trade-offs

- [实体属性结构不统一] → 建立字段映射和针对每类 action 的测试，未知类型不静默修改核心字段。
- [重量单位换算复杂] → 首期只对同单位数值做加法，无法解析时保留为新条目或返回领域错误。
- [remark 语义多样] → set/replace 明确覆盖，add 使用分号追加，remove 按完全匹配或规范化文本移除。

## Migration Plan

1. 新增 context 模型、会话对象和 reducer。
2. 增加 Entity action 到字段的单元测试和序列化测试。
3. 运行全量测试，确认现有 extract、intent、graph、CLI 不受影响。
4. 后续单独 change 将 context 注入 LangGraph state 和 CLI session。
