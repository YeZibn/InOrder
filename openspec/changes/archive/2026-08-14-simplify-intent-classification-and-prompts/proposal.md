## Why

当前主意图包含 `order`、`qa`、`ambiguous` 三种结果，`ambiguous` 会让流程停在额外澄清分支，且现有 prompt 没有清晰定义“执行请求”和“信息询问”的边界。收敛为两种主意图并重写 prompt，可以让路由更直接、输出更稳定，并为后续订单子图提供更明确的输入。

## What Changes

- **BREAKING** 主意图只保留 `order` 和 `qa`，移除 `ambiguous`。
- 明确“存在执行请求时优先判定为 `order`”的混合请求规则。
- 简化 LangGraph 主意图路由，移除 ambiguous/主意图澄清分支。
- 重写主意图识别 prompt，加入定义、边界规则、反例和严格 JSON 输出约束。
- 重写订单子意图 prompt，明确多子意图、参数提取和 `depends_on` 关系规则。
- 保留 `needs_clarification`，但仅用于 order 主意图下未识别出具体子意图或缺少必要信息。
- 更新领域校验、图状态、测试和主规格。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `intent-planning`：主意图枚举从三种收敛为两种，并新增执行优先、prompt 输出和澄清边界要求。
- `langgraph-intent-graph`：移除 ambiguous 路由和节点，保留 order/qa 两分支及统一出口。

## Impact

- 影响 `src/inorder_llm/intent/`、`src/inorder_llm/graph/intent/` 及相关测试。
- 影响主意图 LLM 请求的 system prompt 和子意图 LLM 请求的 system prompt。
- 现有返回 `ambiguous` 的 mock 或调用方需要迁移为 `order` 或 `qa`。
- 不改变订单子意图名称、识别-only 边界、LangGraph 依赖或 CLI 启动方式。
