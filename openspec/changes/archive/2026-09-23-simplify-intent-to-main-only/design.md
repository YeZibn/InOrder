## Context

意图图已经收敛为主意图分类和终态整理，MainGraph 已负责 `order`/`qa` 路由，官方 CLI 也已经构建并注入 MainGraph。当前仍有几处实现和说明没有跟上：事件适配器保留了已删除节点的文案，意图图导入了不参与拓扑的路由函数，README 和 `SYSTEM_GAPS.md` 仍描述旧子意图/旧 full 架构。

此外，`FullChainRunner` 仍有两套编排：提供 MainGraph 时调用父图，未提供时自行顺序调用 IntentRunner 和 OrderRunner。CLI 的 MainGraph QA 结果包含 `qa_placeholder` 和 `order_graph_entered=false`，但 formatter 先处理后者，可能掩盖 QA 占位信息。

## Goals / Non-Goals

**Goals:**

- 将意图识别收敛为一次主意图 LLM 调用。
- 保留严格的 `main_intent` 与 `confidence` 输出校验。
- 让订单完整性和字段变更继续由订单处理链路负责。
- 清理内部模型、图状态、CLI/API/SSE 中的子意图字段。
- 清除已删除节点、无效路由文件和过时文档留下的重构残留。
- 让 MainGraph 成为 `full` 唯一编排来源，并使 QA 终态得到正确展示。

**Non-Goals:**

- 不新增主意图类别。
- 不改变订单 Rewrite、Extract、Reducer、货物画像或车型解析逻辑。
- 不在本 change 中实现问答能力或历史订单查询。
- 不移除 intent 和 order 两条独立调试链路。

## Decisions

1. **意图路由残留**：意图图的拓扑只有 `main_intent -> finalize`，父图负责 `order` 和 `qa` 路由。因此删除意图图对 `route_main_intent` 的无效导入和对应路由模块；事件映射只保留当前图实际可执行的节点。

2. **结果模型**：保留 `IntentPlan` 作为内部结果容器，只承载 `main_intent`、可选 `confidence` 和原始消息；路由与调用方不再依赖子意图步骤或 `depends_on`。对外主意图契约保留 `main_intent` 与可选 `confidence`。

3. **主意图校验**：在模型解析后校验 `main_intent` 属于 `order|qa`，`confidence` 为 0 到 1 的数值；非法结果通过现有结构化修复机制重试一次，仍失败则抛出明确错误。额外字段不参与路由。

4. **完整性边界**：删除意图层的 `needs_clarification` 生成；订单摘要节点根据 pickup、dropoff、cargo、delivery_time 等业务字段决定缺失提示。

5. **Full 链路唯一来源**：`FullChainRunner` 只调用注入的 MainGraph，不再实现 IntentRunner → OrderRunner 的备用编排。`full` 缺少 MainGraph 时返回明确的配置不可用反馈；`intent` 和 `order` 仍可各自独立运行。官方 CLI 已构造 MainGraph，因此正常入口不需要兼容回退。

6. **QA 终态展示**：当 MainGraph 返回 QA 占位结果时，CLI 应优先展示该结果，不得把 `order_graph_entered=false` 当成订单分支未配置。该 change 只保证占位状态正确显示，不实现真实问答。

7. **文档语义**：README 说明主意图分类和 MainGraph 当前结构；`SYSTEM_GAPS.md` 记录 MainGraph 已实现，并把真实问答能力列为尚未实现的业务能力。清理只针对现行文档和活跃代码，不要求抹除 OpenSpec 迁移历史或解释已删除字段的历史测试。

## Risks / Trade-offs

- [外部调用方仍读取 `sub_intents`] → 在发布说明中标记 breaking change，并通过全量测试搜索残留引用。
- [删除子意图后无法表达未来复杂多动作] → 依赖 action 的订单处理已覆盖当前场景；未来多工具编排另建 change。
- [模型输出 confidence 缺失或类型错误] → 统一校验并走一次格式修复，不用默认值掩盖错误。
- [直接构造 CLI 的调用方依赖旧 full 回退] → 给出明确的 MainGraph 配置反馈，并保留 intent/order 独立入口；官方 CLI 路径已经注入 MainGraph。
