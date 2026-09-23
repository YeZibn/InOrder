## Why

原始问题是意图图在主意图识别后还额外调用 LLM 识别 `create_order`/`modify_draft` 子意图，但父图并不使用该结果，订单修改也已由实体 action 和上下文 reducer 处理。主意图收敛已解决这部分重复调用；本次继续完成同一变更的架构和文档收尾，避免实现残留让系统同时存在两套 full 编排来源。

主意图收敛已经落地，但收尾仍不完整：事件适配器和 README 留有旧子意图节点描述，意图图还导入了未参与拓扑的旧路由函数，`SYSTEM_GAPS.md` 也把已经存在的 MainGraph 描述成尚未实现。CLI 的 `FullChainRunner` 同时保留 MainGraph 和 Python 顺序串联两套 full 实现，形成两个编排来源；MainGraph 的 QA 终态结果还可能被 CLI 格式化成“订单处理未进入”。

## What Changes

- **BREAKING** 删除子意图识别及其 `create_order`、`modify_draft`、`depends_on` 契约。
- 意图图只输出 `order` 或 `qa` 主意图及置信度，并据此进行父图路由。
- 删除意图图中的子意图节点、子意图 Prompt、步骤模型和依赖校验。
- 从意图结果、CLI 展示和 API/SSE 业务结果中移除 `sub_intents` 字段。
- 订单创建、修改和必要字段检查继续由订单处理图、实体 action、上下文 reducer 和订单摘要完成。
- 增加主意图边界、结果兼容和子意图不再调用的测试。
- 清理 `_NODE_TEXT`、意图路由模块、README 和 `SYSTEM_GAPS.md` 中已失效的子意图与旧架构描述。
- 将 MainGraph 定为 `full` 链路唯一编排来源；缺少 MainGraph 时给出明确配置反馈，不再回退到 IntentRunner 与 OrderRunner 的 Python 顺序串联。
- 修正 MainGraph QA 终态在 CLI 中的展示，并覆盖 MainGraph 的订单、QA 与缺少配置分支。

## Capabilities

### New Capabilities

### Modified Capabilities

- `intent-planning`: 意图计划收敛为主意图分类结果，删除子意图和步骤依赖。
- `main-parent-graph`: 父图仅依据主意图路由，移除子意图结果字段。
- `intent-cli`: 意图链路和 full 链路不再展示子意图内容。

## Impact

- 影响 `src/inorder_llm/intent`、意图 LangGraph、父图汇总、CLI runner 与结果格式化、工作流事件适配器、README、`SYSTEM_GAPS.md` 和相关测试。
- 这是对内部意图结果结构的 breaking change；保留 `main_intent` 与 `confidence` 作为稳定字段。依赖 CLI 隐式顺序串联、但未提供 MainGraph 的调用方需要显式配置 MainGraph。
- 不改变订单实体提取、action 合并、货物画像、车型解析和订单完整性摘要逻辑。
