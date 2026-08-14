## 1. 建立分层目录与基础抽象

- [x] 1.1 创建 `graph/`、`graph/intent/`、`graph/intent/nodes/`、`intent/`、`infrastructure/llm/`、`cli/` 和 `commands/` 包结构
- [x] 1.2 实现轻量 `BaseNode` 与 `BaseGraph`，补充最小单元测试
- [x] 1.3 将 LLM 基础设施模块迁移到 `infrastructure/llm/`，保持行为不变

## 2. 重组意图领域与 LangGraph

- [x] 2.1 将 `IntentPlan`、`IntentStep`、异常、协议和校验逻辑拆分到 `intent/` 模块
- [x] 2.2 将 `IntentGraphState` 拆到 `graph/intent/state.py`
- [x] 2.3 将主意图、子意图、计划构建、校验、澄清节点拆到 `graph/intent/nodes/`
- [x] 2.4 将条件路由拆到 `graph/intent/routing.py`
- [x] 2.5 实现 `IntentGraph` builder/compile，并确保主意图与子意图仍是独立 LangGraph 节点

## 3. 兼容入口与 CLI 解耦

- [x] 3.1 将 `intent_graph.py` 改为兼容转发模块，保留 `build_intent_graph`
- [x] 3.2 将 CLI 会话、命令解析和格式化拆分到 `cli/`，将命令入口拆到 `commands/`
- [x] 3.3 保留 `inorder`、`llm-verify` 入口及现有 `/intent` 等命令行为
- [x] 3.4 收敛包级 `__init__.py` 导出，保留必要公共 API

## 4. 验证与文档

- [x] 4.1 更新测试 import 和新增结构边界测试
- [x] 4.2 在 conda `agent` 环境运行全量测试
- [x] 4.3 验证 `python -m`、`inorder` 和 `llm-verify` 入口
- [x] 4.4 更新 README 中的目录、导入示例和运行说明
