## Context

当前正式图实现集中在 `inorder_llm.intent_graph`，其中同时定义了 LangGraph 状态、节点函数、条件路由和 builder；意图模型与旧 facade 位于 `intent_planning.py`。本次重构必须继续支持 Python 3.9、现有 LangGraph 依赖、recognition-only 约束和已有命令入口。

## Goals / Non-Goals

**Goals:**

- 建立 `graph/` 作为 LangGraph 编排层，并将意图图拆成状态、节点、路由和 graph builder。
- 提供轻量 `BaseNode` 与 `BaseGraph` 抽象，节点可直接注册到 LangGraph，避免自建运行时。
- 将 `IntentPlan` 等领域模型与 LangGraph state 分离。
- 通过兼容模块保留现有 import 路径和 CLI 行为。
- 让 `IntentGraph` 成为唯一正式的图构建实现。

**Non-Goals:**

- 不迁移顶层包名 `inorder_llm`。
- 不增加订单查询、草稿修改、创建订单、确认下单或真实问答节点。
- 不引入数据库、checkpoint、interrupt、流式执行或新的外部依赖。
- 不改变识别结果字段、路由语义和 LLM 请求协议。

## Decisions

### 目录按职责分层

采用 `inorder_llm/graph/intent/`，下设 `state.py`、`nodes/`、`routing.py` 和 `graph.py`。LLM client 继续留在基础设施层，意图模型移动到 `intent/` 领域层，CLI 独立到 `cli/` 与 `commands/`。相比继续平铺模块，这种布局能让未来新增订单图时复用 graph 基础设施而不污染意图领域。

### 使用轻量基类，不封装 LangGraph runtime

`BaseNode` 提供 `name` 和 `__call__ -> run` 约定；`BaseGraph` 提供 `build()` 和 `compile()`。具体节点仍返回 LangGraph 要求的局部 state update，图仍由官方 `StateGraph` 编译。相比复杂模板方法或自定义 DAG runtime，轻量抽象更容易调试，也不会隐藏 LangGraph 行为。

### 状态与领域模型分离

`IntentGraphState` 只描述图执行中间状态；`IntentPlan`、`IntentStep` 归入意图领域模型。图出口继续返回包含 `intent_plan` 的统一状态，CLI 只消费该结果，不直接依赖节点实现。

### 兼容转发而非立即删除旧模块

`intent_graph.py` 保留 `build_intent_graph` 转发到新 `IntentGraph`；必要时保留旧 planning facade 作为兼容层并标注 deprecated。这样可以逐步迁移内部 import，降低一次性目录移动风险。

### 节点依赖通过构造函数注入

主意图和子意图节点接收 `IntentModel`，不直接创建 LLM client。图 builder 接收模型并组装节点，保证测试可以使用 mock，也避免 graph 层依赖具体供应商 SDK。

## Risks / Trade-offs

- [旧 import 遗漏] → 保留兼容转发，并用全量测试、`python -m` 和安装后入口验证。
- [循环依赖] → 约束依赖方向为 `commands/cli → graph → intent → infrastructure`，基础设施不反向依赖上层。
- [基类过度设计] → 首期只保留 `BaseNode`、`BaseGraph` 两个薄抽象，不引入注册表、插件系统或复杂生命周期。
- [包结构变化影响打包] → 使用 setuptools 自动发现包，并验证 editable install 后的 `inorder`、`llm-verify`。

## Migration Plan

1. 新增目录和模块，将现有实现迁移到新位置。
2. 添加兼容转发模块，修正内部和测试 import。
3. 运行 conda `agent` 环境下的全量测试及 CLI/LLM 冒烟检查。
4. 确认行为一致后，再在后续 change 中考虑删除 deprecated facade 或迁移包名。
