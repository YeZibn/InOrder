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

当前版本支持同步文本调用和用于订单语义解析的 LangGraph 子图；不包含流式输出、工具调用或外部订单服务。

## 意图规划子图

意图识别阶段只输出计划，不执行订单业务。主意图只区分 `order` 与 `qa`：含明确订单执行请求即为 `order`，纯信息或操作方法询问为 `qa`；混合消息按「执行优先」归为 `order`。

```python
from inorder_llm.graph.intent import build_intent_graph

graph = build_intent_graph(your_intent_model)
result = graph.invoke({"message": "参考最近历史订单，修改当前草稿"})
plan = result["intent_plan"]
# plan.sub_intents: query_history_order -> modify_draft
```

`IntentPlan` 支持主意图、多个订单子意图、步骤参数和 `depends_on`；后续主图可以根据该计划路由到业务子图。

图相关代码按职责位于 `inorder_llm/graph/`：

```text
graph/
├── base.py
└── intent/
    ├── state.py
    ├── routing.py
    ├── graph.py
    └── nodes/
```

`BaseNode` 只统一节点调用边界，`BaseGraph` 只统一 build/compile；底层仍直接使用官方 LangGraph `StateGraph`。图中 `main_intent` 和 `sub_intent` 是两个独立节点；只有主意图为 `order` 时才会进入子意图节点。当 `order` 未识别出具体子意图时，计划会标记 `needs_clarification`。

## 交互式 CLI

安装项目后启动（建议先激活 conda `agent` 环境）：

```bash
inorder
```

CLI 提供三条可切换链路：

```text
full    完整链路：意图图 → order 时进入订单处理子图
intent  意图链路：只运行意图图
order   下单链路：只运行订单处理子图
```

支持：

```text
/chain              选择链路提示
/chain full         切换完整链路
/chain intent       切换意图链路
/chain order        切换下单链路
/intent             兼容命令，切换意图链路
/mode               查看当前链路或兼容模式
/context            以 JSON 查看当前订单上下文
/conversation       以 JSON 查看当前会话历史
/clear              清空本地消息、历史和订单上下文
/help               查看命令
/exit               退出
```

`full` 链路识别为 `order` 时会继续进入 rewrite → clarification → extract → context update 订单处理子图；`intent` 和 `order` 可用于单独调试对应链路。当前 CLI 只做意图识别、订单语义解析和内存订单上下文更新，不执行归一化、历史订单查询、草稿修改、创建订单、确认下单或真实问答。

普通消息成功处理后，CLI 会在当前内存会话中追加一条精简的 assistant 处理摘要；不会保存完整实体 JSON、订单上下文、原始 LLM content 或错误堆栈。`/context` 和 `/conversation` 是只读查看命令，不会调用 graph 或修改会话。

如果不安装命令入口，也可以使用：

```bash
PYTHONPATH=src python -m inorder_llm.commands.intent_chat
```

### Grounded Extract

订单实体提取默认使用 `langextract==1.6.0`。它保留原文片段、字符位置与对齐状态，再映射为现有的 `Entity`，供订单上下文 reducer 消费；`action`、地址角色及其他业务 attributes 必须由 LLM 输出，adapter 不会补默认值或按关键词重新判断。

提取只消费 rewrite 生成的本轮文本和参考时间；历史对话与订单上下文只用于 rewrite，避免把已有订单字段重新提取为本轮变更。LangExtract 的 prompt 与 schema-covering examples 定义在 `extract/resolver.py`。

`EXTRACTOR_BACKEND=langextract` 为默认配置。LangExtract 调用失败时不会自动回退，避免同一会话混用两种提取语义。仅在迁移排障时可显式设为 `EXTRACTOR_BACKEND=json` 使用旧 JSON 提取器，问题排除后应恢复默认值。

可选的真实网关验证不会在普通测试中运行：

```bash
INORDER_LLM_LIVE_TESTS=1 conda run -n agent python -m pytest -s -q tests/test_langextract_adapter.py
```

### LLM 多角色身份探针

项目提供一个默认跳过的真实网关探针，用于检查模型在多角色指令下是否仍能识别自身身份并遵守 JSON 输出格式。运行时会打印每次 LLM 返回的原始 `content`：

```bash
INORDER_LLM_LIVE_TESTS=1 conda run -n agent python -m pytest -s -q tests/test_prompt_role_identity.py
```

该探针不要求固定的模型名称，但要求返回非空 JSON，并包含 `identity`、`active_roles` 和 `format_compliant` 字段。
