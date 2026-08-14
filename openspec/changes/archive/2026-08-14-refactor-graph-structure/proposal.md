## Why

当前 Python 包将 LLM 基础设施、意图领域、LangGraph 图实现和 CLI 平铺在同一目录，且同时存在正式 StateGraph 与旧的 facade，导致职责边界和唯一入口不清晰。现在先进行结构化重组，可以为后续订单图和问答图扩展提供稳定边界，同时避免改变已经验证的意图识别行为。

## What Changes

- 新增 `graph/` 编排层，按图、状态、路由和节点组织 LangGraph 代码。
- 为图和节点提供轻量、可复用的基类或协议，统一构建与调用边界。
- 将意图领域模型、LLM 适配器、图运行状态和 CLI 会话状态分离。
- 将意图图收敛为唯一正式的 LangGraph 入口，同时保留现有导入和命令入口的兼容转发。
- 不改变主意图、子意图、依赖关系、recognition-only 边界及现有 CLI 行为。
- 不在本 change 中迁移顶层包名 `inorder_llm`，也不新增订单业务节点。

## Capabilities

### New Capabilities

无。本 change 是纯结构重构，不改变外部可观察需求，因此通过 `skip_specs: true` 跳过 delta spec。

### Modified Capabilities

无。

## Impact

- 受影响代码：`src/inorder_llm/` 下的图、意图规划、LLM 适配和 CLI 模块，以及对应测试和打包入口。
- 兼容性：保留 `inorder_llm.intent_graph.build_intent_graph`、`inorder` 和 `llm-verify` 入口，调用方无需立即迁移。
- 依赖：继续使用现有 LangGraph、OpenAI-compatible client 和 conda `agent` 环境。
- 风险：模块移动可能暴露循环依赖或旧导入遗漏，需要通过全量测试和入口冒烟验证。
