## Context

当前订单处理子图由 rewrite 根据 `needs_clarification` 在 clarification 和 extract 之间分流。RewriteResult、OrderGraphState 和 CLI 也携带澄清字段。此次变更会把 rewrite 变为纯重写步骤，并保持意图规划层的澄清独立存在。

## Goals / Non-Goals

**Goals:**

- 让合法 rewrite 结果始终进入实体提取和上下文更新。
- 简化 rewrite 输出和订单子图状态。
- 让 CLI 只展示实际执行的 rewrite、extract 和实体结果。
- 保留 JSON 结构错误和 LLM 响应校验。

**Non-Goals:**

- 不删除 intent planning 的澄清能力。
- 不新增本地歧义解析或关键词规则。
- 不改变实体提取、订单上下文合并和货物画像逻辑。

## Decisions

### 1. 删除 rewrite 澄清字段

RewriteResult 只保留两个文本字段。相比保留固定为 false 的兼容字段，直接移除可以防止下游继续把 rewrite 当作阻断节点。

### 2. 固定图路由

LangGraph 直接连接 rewrite → extract，删除 conditional route 和 clarification node。非法 JSON 仍在 resolver 解析阶段抛出结构化错误。

### 3. 最佳努力解释

Prompt 要求模型使用当前上下文选择最合理的指代解释，并生成非空 extraction_text。模型无法完全确定时也继续输出，而不是返回澄清状态。

## Risks / Trade-offs

- [歧义输入可能被错误解释] → 通过 rewrite_text 和 extraction_text 输出保留可观察结果，后续业务校验仍可拒绝不合法实体。
- [下游调用者依赖旧澄清字段] → 同步更新模型、状态、runner、CLI 和测试，作为 breaking change 一次性迁移。
- [主意图澄清概念混淆] → 明确只移除订单 rewrite 澄清，intent planning 维持原契约。
