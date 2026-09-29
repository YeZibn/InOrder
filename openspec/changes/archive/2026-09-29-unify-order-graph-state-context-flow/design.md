## Context

当前订单图用 `OrderGraphState.order_context` 承载累计订单快照；本轮 `entities` 是提取结果；车型结果和完整性摘要是本轮派生结果。`normalize_entities` 已分发时间、手机号、枚举和车型/规格归一化，但 Reducer 与车型节点各自调用它；Reducer 还会再次按目录查找车型和规格。MainGraph 执行时需要根级工作 `order_context`，Finalize 又把该值放入 `order_result`，而完整结果仍保留根级字段。

相关行为要求见 `specs/order-processing-subgraph/spec.md`、`specs/conversation-order-context/spec.md`、`specs/main-parent-graph/spec.md` 和 `specs/cli-chain-entrypoints/spec.md`。车型生命周期、候选排序和提交规则不在本设计范围内。

## Goals / Non-Goals

**Goals:**

- 让每个节点能明确判断应读取本轮输入、当前工作订单快照、本轮变更指令还是本轮派生结果。
- 只在一个边界归一化实体，并让 reducer 与车型处理共用结果。
- 在调用方看到稳定且唯一的订单上下文路径，并仅在完整成功后更新会话。

**Non-Goals:**

- 不将 `OrderContext` 展开复制到另一份大型 state model，也不改造所有字段为多层嵌套对象。
- 不改变车型匹配算法、用户指定车型优先级、上下界适配等级或货物画像算法。
- 不改变 SSE 事件名称、顺序或 token streaming 行为。
- 不引入数据库、checkpoint 或服务端会话持久化。

## Decisions

### 1. 将 `OrderContext` 作为工作状态中的唯一累计订单快照

图的输入 `OrderContext` 是只读起点。订单图在自己的运行状态中持有一份当前工作快照，各节点通过返回新快照推进流程；不在 state 的其他顶层字段重复存储 `vehicle_type`、货物、地址等累计事实。`cargo_profiles` 和其摘要仍属于 `OrderContext`，因为它们是基于完整货物集合、供后续轮次和节点复用的派生状态；车型候选、车型原因和完整性摘要仍属于本轮结果。

`GraphState` 继续是执行工作区，而不是第二个 `OrderContext`。为避免无益迁移，本 change 保留现有浅层请求/结果字段布局，只收敛字段所有权；不要求把 `request`、`turn`、`derived` 再包成嵌套 TypedDict。每个字段的用途在 state 类型和节点输入约定中注明。

考虑过把 state 直接设计成 context 的镜像，并在 Finalize 时一次性写回。该方式被否决：货物画像、车型解析和完整性检查都需要本轮实体合并后的订单值；延迟 reducer 会令它们读取旧值，或迫使每个节点各自模拟一次合并。

### 2. 由一个图节点统一调度实体归一化，然后立即应用 reducer

节点顺序固定为：

```text
Rewrite → Extract → NormalizeEntities → ContextUpdate
        → CargoProfile（货物变化时）→ VehicleResolution（启用时）
        → OrderCompleteness → Finalize
```

NormalizeEntities 是图中的一个独立边界节点，统一调度现有的领域归一化规则，而不是把这些规则揉成一个大型实现。当前适用类型为时间、手机号、支付/发票/跟车/服务枚举、车型和车型规格；每类规则继续由自己的纯函数完成。不需要归一化的实体原样通过。节点把结果写回唯一的本轮 `entities` 状态字段，同时保留原始表达、action 和匹配状态，不再另存一套 raw/normalized 列表。

归一化节点沿用每类规则现有的错误策略：非法时间、手机号或枚举在上下文更新前失败；车型或规格无法唯一匹配时保留原始表达和未匹配状态，继续进入现有 action/车型决策路径。此 change 不把宽松车型匹配改成严格报错，也不改变各领域归一化规则本身。

ContextUpdate 只应用已经归一化的实体 action，不在 Reducer 内重复归一化，也不对车型原文重复执行目录或模糊匹配；合法 canonical code 的结构校验可以保留。`OrderContextReducer.apply` 的调用契约因此变为“输入已归一化的实体”；图节点之外的直接调用方也必须显式先调用统一归一化入口，再应用 action。VehicleResolution 直接消费同一份实体状态，读取未匹配表达的原文及 action，并与更新后的 `OrderContext` 合并使用。Reducer 对传入 context 做复制并返回新快照，避免图内更新污染调用方的输入对象。

统一节点只处理本轮提取实体。城市名规范化仍属于车型目录查询边界，车型关键词清理仍属于匹配器内部，货物画像仍是读取完整货物集合的派生阶段；这些工作不迁入实体归一化节点。工作流适配器不新增归一化专属公开进度事件，以维持现有 SSE 阶段语义。

ContextUpdate 必须早于依赖累计订单数据的节点。货物变化时，CargoProfile 从更新后的完整 `cargo` 重建画像并整体替换旧画像；VehicleResolution 从当前工作 `OrderContext` 读取车型来源、规格、货物画像及地址，同时仅从本轮实体读取当前车型表达和 action。完整性检查读取车型处理后的 context 与本轮车型结果。

### 3. 区分图内推进与跨轮提交

Reducer 在图内更新工作快照，不代表会话或外部存储已提交。只有图所有必需节点成功且 Runner 收到完整结果后，CLI 才将最终 context 赋给 session；失败时保留原 session context。SSE 仍只发送现有公开事件，成功的 `CREATE_ORDER_CONTEXT` 和 `DONE` 使用完整结果中的同一份 context。

### 4. 在结果边界统一返回结构

订单图内部仍可使用根级 `order_context` 作为节点间状态通道。对调用方暴露的 order/full Runner 结果统一为：

```text
order chain: { order_result: { entities, order_context, vehicle_resolution, ... } }
full chain:  { intent_result, order_result: { entities, order_context, ... } }
```

OrderChainRunner 将订单子图原始 state 放进 `order_result`；FullChainRunner 保持同样的订单子结构。MainGraph 使用独立的输出投影，只暴露 `intent_result`、可用时的 `order_result` 及必要的非业务终态字段，不把内部根级 `order_context` 再带到调用方结果。CLI 和工作流适配器从 `order_result.order_context` 读取订单快照；不提供根级兼容别名。

这样既保留图内部传递所需的单一根级工作状态，也把重复数据挡在调用边界内。直接依赖 `OrderChainRunner` 根级字段的内部调用方需要在同一变更中迁移。

### 5. 保持现有车型规则

本 change 只调整车型节点读到的数据来源，不更改车型状态规则：已匹配的用户车型仍按既有规则保留；候选排序和 `lower_bound_fit`、`upper_bound_only` 的提交行为保持不变；未匹配的原始车型表达仍可用于解析结果的说明。车型解析结果是本轮结果，最终生效车型仍由工作 `OrderContext` 表示。

## Risks / Trade-offs

- **[Runner 结果结构是内部兼容性变更]** → 在同一提交中迁移 CLI 的 order/full 消费方和相关测试；不保留第二个根级 context 别名。
- **[`OrderContextReducer.apply` 输入契约改变]** → 检查并迁移所有直接调用方及测试，让它们先归一化实体，再应用 action；不在 Reducer 内保留隐式兼容归一化。
- **[NormalizeEntities 可能改变原始实体输出]** → 保留原始表达与 action 元数据；添加未匹配车型表达可到达车型处理的验证。
- **[父图输出投影可能漏掉现有消费者所需字段]** → 先核对 CLI、工作流事件适配器及所有 MainGraph 调用方，再以显式字段清单构造投影；SSE 事件协议保持原样。
- **[错误地在失败后提交会话状态]** → 在图返回完整成功结果前不赋值 session；覆盖 reducer 后下游失败的回归场景。

## Migration Plan

1. 先引入统一实体处理节点和工作状态读取约定，将所有直接调用 Reducer 的生产调用方和测试迁移为先归一化、再应用 action，并更新顺序测试。
2. 更新订单/full Runner 与 MainGraph 的调用结果投影，再迁移 CLI 和工作流结果读取路径。
3. 验证会话只在成功后保存唯一结果 context，并验证 SSE 事件字段与时序未变。
4. 若迁移出现问题，回滚 Runner/输出投影与 state 流程改动；无需数据迁移，因为 `OrderContext` 的序列化字段不变。

## Open Questions

无。调用方范围、结果形状和车型规则边界已在本设计中确定。
