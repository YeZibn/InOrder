## Why

当前意图图在主意图识别后还会额外调用一次 LLM 识别 `create_order`/`modify_draft` 子意图，但父图不使用该结果进行路由，订单修改也已由实体 action 和上下文 reducer 处理。这次重复识别增加了延迟、成本和结构化输出失败点，且让意图层承担了订单完整性判断职责。

## What Changes

- **BREAKING** 删除子意图识别及其 `create_order`、`modify_draft`、`depends_on` 契约。
- 意图图只输出 `order` 或 `qa` 主意图及置信度，并据此进行父图路由。
- 删除意图图中的子意图节点、子意图 Prompt、步骤模型和依赖校验。
- 从意图结果、CLI 展示和 API/SSE 业务结果中移除 `sub_intents` 字段。
- 订单创建、修改和必要字段检查继续由订单处理图、实体 action、上下文 reducer 和订单摘要完成。
- 增加主意图边界、结果兼容和子意图不再调用的测试。

## Capabilities

### New Capabilities

### Modified Capabilities

- `intent-planning`: 意图计划收敛为主意图分类结果，删除子意图和步骤依赖。
- `main-parent-graph`: 父图仅依据主意图路由，移除子意图结果字段。
- `intent-cli`: 意图链路和 full 链路不再展示子意图内容。

## Impact

- 影响 `src/inorder_llm/intent`、意图 LangGraph、父图汇总、CLI/API/SSE 序列化和相关测试。
- 这是对内部意图结果结构的 breaking change；保留 `main_intent` 与 `confidence` 作为稳定字段。
- 不改变订单实体提取、action 合并、货物画像、车型解析和订单完整性摘要逻辑。
