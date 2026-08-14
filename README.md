# InOrder LLM Client

这是一个面向后续 LangGraph 工作流的 Python、OpenAI-compatible LLM 调用基础层。

## 本地验证

使用 conda `agent` 环境安装项目依赖：

```bash
conda run -n agent python -m pip install -e '.[dev]'
```

配置 `.env.example` 中的环境变量后，可运行：

`LLM_REASONING_EFFORT` 可设置为 `low`、`medium` 或 `high`；留空时不向上游发送该可选参数。

```bash
conda run -n agent llm-verify "请用一句话问候我"
```

也可以不安装命令入口：

```bash
PYTHONPATH=src conda run -n agent python -m inorder_llm.commands.llm_verify
```

## LangGraph 预留方式

后续节点只需注入 `LLMClient`，不需要依赖 OpenAI SDK 的响应类型：

```python
from inorder_llm import ChatMessage, LLMClient

def call_llm(state, client: LLMClient):
    response = client.chat(state["messages"])
    return {"messages": [ChatMessage("assistant", response.text)]}
```

当前版本只支持同步文本调用，不包含 LangGraph 图、订单状态、流式输出或工具调用。

## 意图规划子图

意图识别阶段只输出计划，不执行订单业务：

```python
from inorder_llm.intent import IntentPlanningSubgraph

graph = IntentPlanningSubgraph(model=your_intent_model)
plan = graph.invoke("参考最近历史订单，修改当前草稿")
# plan.sub_intents: query_history_order -> modify_draft
```

`IntentPlan` 支持主意图、多个订单子意图、步骤参数和 `depends_on`；后续主图可以根据该计划路由到业务子图。

当前已提供真正的 LangGraph StateGraph 入口。图相关代码按职责位于 `inorder_llm/graph/`：

```text
graph/
├── base.py
└── intent/
    ├── state.py
    ├── routing.py
    ├── graph.py
    └── nodes/
```

`BaseNode` 只统一节点调用边界，`BaseGraph` 只统一 build/compile；底层仍直接使用官方 LangGraph `StateGraph`。

```python
from inorder_llm.graph.intent import build_intent_graph
```

兼容入口仍然可用：

```python
from inorder_llm.graph.intent import build_intent_graph

graph = build_intent_graph(your_intent_model)
result = graph.invoke({"message": "参考历史订单修改当前草稿"})
```

图中 `main_intent` 和 `sub_intent` 是两个独立节点；只有主意图为 `order` 时才会进入子意图节点。

## 交互式 CLI

安装项目后启动（建议先激活 conda `agent` 环境）：

```bash
inorder
```

支持：

```text
/intent             选择模式提示
/intent auto        切换自动模式
/intent order       切换订单意图模式
/intent qa          切换问答占位模式
/intent plan        输出结构化 IntentPlan
/mode               查看当前模式
/clear              清空本地会话消息
/help               查看命令
/exit               退出
```

CLI 当前只做意图识别，不查询历史订单、不修改草稿、不创建订单、不确认下单，也不回答真实问答。

如果不安装命令入口，也可以使用：

```bash
PYTHONPATH=src python -m inorder_llm.commands.intent_chat
```
