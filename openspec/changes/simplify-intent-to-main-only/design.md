## Context

当前意图图依次执行主意图、子意图、计划构建、校验和终态节点；父图只读取主意图路由，订单处理图则根据重写文本和实体 action 完成实际创建/修改。变更需要删除无业务价值的子意图分支，同时保持 `order`/`qa` 路由和订单结果结构稳定。

## Goals / Non-Goals

**Goals:**

- 将意图识别收敛为一次主意图 LLM 调用。
- 保留严格的 `main_intent` 与 `confidence` 输出校验。
- 让订单完整性和字段变更继续由订单处理链路负责。
- 清理内部模型、图状态、CLI/API/SSE 中的子意图字段。

**Non-Goals:**

- 不新增主意图类别。
- 不改变订单 Rewrite、Extract、Reducer、货物画像或车型解析逻辑。
- 不在本 change 中实现问答能力或历史订单查询。

## Decisions

1. **意图图拓扑**：保留 `main_intent -> finalize` 主路径；`order` 和 `qa` 的分支路由由父图负责。删除 `SubIntentNode` 及其相关节点和依赖校验。相比“保留节点但不调用”，完整删除可避免死代码和隐藏 LLM 成本。

2. **结果模型**：将 `IntentPlan` 简化为主意图结果，或在内部直接使用映射结构；对外统一保留 `main_intent` 与可选 `confidence`。不输出空的 `sub_intents`，避免调用方误以为仍支持步骤编排。

3. **主意图校验**：在模型解析后校验 `main_intent` 属于 `order|qa`，`confidence` 为 0 到 1 的数值；非法结果通过现有结构化修复机制重试一次，仍失败则抛出明确错误。额外字段不参与路由。

4. **完整性边界**：删除意图层的 `needs_clarification` 生成；订单摘要节点根据 pickup、dropoff、cargo、delivery_time 等业务字段决定缺失提示。

5. **兼容策略**：这是内部结果契约的 breaking change。同步删除测试、规格和 CLI 展示中的子意图引用；`main_intent` 字段保持不变，供已有父图路由使用。

## Risks / Trade-offs

- [外部调用方仍读取 `sub_intents`] → 在发布说明中标记 breaking change，并通过全量测试搜索残留引用。
- [删除子意图后无法表达未来复杂多动作] → 依赖 action 的订单处理已覆盖当前场景；未来多工具编排另建 change。
- [模型输出 confidence 缺失或类型错误] → 统一校验并走一次格式修复，不用默认值掩盖错误。
