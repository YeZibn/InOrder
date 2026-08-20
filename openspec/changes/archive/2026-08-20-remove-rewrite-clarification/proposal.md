## Why

当前 rewrite 在语义不唯一时会进入 clarification 节点并跳过实体提取，导致订单解析链路被模糊表达阻断。当前阶段更需要让 LLM 尽力重写并继续提取，再由后续上下文和业务校验处理结果。

## What Changes

- **BREAKING** 移除 rewrite 输出中的 `needs_clarification` 和 `clarification_reason` 字段。
- **BREAKING** rewrite 完成后始终进入 extract，不再通过 clarification 节点分流。
- 删除订单子图中的 clarification 节点及相关状态、CLI 输出和摘要逻辑。
- 更新 rewrite prompt，要求对不明确指代选择最合理的上下文解释并继续生成 extraction_text。
- 保留 LLM JSON 格式、字段类型和非法响应校验。
- 保留意图规划层独立的澄清能力，不在本 change 中移除。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `order-rewrite`: rewrite 输出不再包含澄清状态，必须生成可提取文本。
- `order-processing-subgraph`: rewrite 后固定进入 extract，移除 clarification 分支。
- `cli-chain-entrypoints`: CLI 不再展示 rewrite 澄清和 extract 跳过状态。

## Impact

- 影响 `src/inorder_llm/rewrite/`、`src/inorder_llm/graph/order/` 和 `src/inorder_llm/cli/`。
- 影响 RewriteResult、OrderGraphState、订单子图输出和相关测试。
- 不改变主意图/子意图规划的澄清逻辑，也不改变 JSON 解析错误处理。
