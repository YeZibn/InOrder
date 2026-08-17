## Context

当前 `IntentCli` 只有 `auto`、`order`、`qa`、`plan` 模式，并只持有意图图。项目现在同时存在主意图图和独立订单处理子图，需要在 CLI 层提供可切换的三条调试链路。

## Goals / Non-Goals

**Goals:**

- 用 `full`、`intent`、`order` 统一表示三条运行链路。
- 通过 `/chain` 切换链路，并保留 `/intent` 兼容入口。
- 为 full 链路组合意图图和订单处理子图。
- 为 order/full 链路维护 `HistoryConversation`、`OrderContext` 和参考时间输入。
- 保持可注入 graph runner，测试不访问真实 LLM 服务。

**Non-Goals:**

- 不接入 normalization、reducer 或持久化。
- 不执行真实问答和订单业务。
- 不改变 LangGraph 节点内部契约。

## Decisions

### 用 chain 替代 mode 作为主概念

CLI 选择的是执行哪条图链路，而不是 LLM 的识别模式，因此使用 `chain` 命名。内部保留旧接口的兼容处理，避免已有调用方立即失效。

### 三个可注入 runner

CLI 通过 `IntentChainRunner`、`OrderChainRunner` 和 `FullChainRunner`（或等价适配层）隔离图组装。`handle_message` 只负责记录输入并调用当前 runner，不直接编排节点。

### Full 链路按主意图条件组合

full runner 先调用意图图；`qa` 只返回意图结果和未实现问答状态，`order` 才传递共享上下文调用订单处理子图。

### 会话上下文在 CLI 持有

CLI session 持有 `HistoryConversation`、`OrderContext` 和参考时间。每轮输入可注入这些对象；由于当前订单子图是只读解析，`OrderContext` 在本次 change 中不由 entities 自动更新。

### 结构化链路输出

每条链路都输出链路名和解析-only 状态。intent 输出 IntentPlan，order 输出 RewriteResult/Entity，full 输出两阶段结果，避免用户误以为已经下单。

full 和 order 的订单处理结果还必须暴露可观察的阶段状态：

- `order_graph_entered`：是否进入订单处理子图
- `rewrite_completed`：rewrite 是否完成
- `extract_executed`：extract 是否实际执行
- `extract_skipped_reason`：extract 被跳过时的原因
- `entity_count`：extract 返回的实体数量

成功提取时，CLI 至少展示：

```text
订单处理：已进入
Rewrite：已完成
澄清：否
Extract：已执行
实体数量：N
```

rewrite 触发澄清时，CLI 至少展示：

```text
订单处理：已进入
Rewrite：已完成
澄清：是
Extract：已跳过
原因：...
```

full 链路不得仅输出 Rewrite 文本而不说明 extract 的执行或跳过状态。

## Risks / Trade-offs

- [旧 mode 行为与新 chain 概念不完全一致] → 保留 `/intent` 兼容别名，并在帮助中明确新命令。
- [full 链路需要同时维护两种图状态] → 用 runner 适配层组合，不把两个状态 TypedDict 强行合并。
- [OrderContext 当前不会自动累积] → 输出明确标记仅解析，后续 reducer change 再接入状态更新。

## Migration Plan

先扩展 CLI 和测试，旧的 `inorder` 启动命令保持不变。默认链路设为 `full`；若用户只想调试某一部分，可通过 `/chain intent` 或 `/chain order` 切换。失败时可回退到 `intent` 链路继续使用现有能力。
