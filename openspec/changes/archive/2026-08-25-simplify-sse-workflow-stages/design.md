## Context

当前 `WorkflowEventAdapter` 同时观察父图节点并根据最终状态补发订单子图内部阶段，导致 rewrite、extract、update_context 等实现细节进入 SSE。父图和订单子图本身无需改变。

## Goals / Non-Goals

**Goals:**

- 建立稳定的业务阶段白名单。
- 将订单内部解析步骤聚合为一个“处理订单”阶段。
- 仅在实际执行时展示货物画像和车型阶段。
- 保持事件类型、接口格式、同步图结果和 CLI 兼容。

**Non-Goals:**

- 不修改 LangGraph 节点和边。
- 不改变 LLM 调用、订单上下文合并或车型估算逻辑。
- 不引入 token 级 SSE。

## Decisions

1. **使用公开阶段白名单。** `intent`、`order`、`cargo_profile`、`vehicle` 是唯一允许出现在 `THINKING_STEP.stage` 的阶段值。未知或内部节点不直接透传。

2. **订单阶段聚合。** 父图进入 `order_subgraph` 时发布 `order` 阶段；最终状态回退推断时，只要进入订单链路且存在订单结果，也最多补发一次 `order`，不再根据 `rewrite_result`、`entities` 或 `order_context` 分别发送阶段。

3. **可选阶段由结果决定。** `cargo_profile` 仅在画像实际更新时发布，`vehicle` 仅在车型结果实际存在时发布。

4. **保留数据事件。** `CREATE_ORDER_CONTEXT` 不是思考阶段，继续在上下文确实更新时发送结构化快照。

## Risks / Trade-offs

- [Risk] 用户无法看到订单解析的细分进度 → Mitigation: 通过阶段标题和最终结构化结果保持可理解性，细节保留在服务日志和内部测试。
- [Risk] 未来增加业务阶段需要更新白名单 → Mitigation: 将阶段映射集中在事件适配层并用顺序测试锁定契约。
