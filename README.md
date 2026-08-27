# InOrder LLM Client

这是一个面向后续 LangGraph 工作流的 Python、OpenAI-compatible LLM 调用基础层。

## 本地验证

使用 conda `agent` 环境安装项目依赖：

```bash
conda run -n agent python -m pip install -e '.[dev]'
```

配置 `.env.example` 中的环境变量后，可运行：

`LLM_REASONING_EFFORT` 可设置为 `low`、`medium` 或 `high`；留空时不向上游发送该可选参数。

`LLM_API_MODE` 可设置为 `chat_completions` 或 `responses`，默认使用 `chat_completions`。`LLM_BASE_URL` 始终填写服务根路径，例如 `https://example.com/v1`，不要把具体 endpoint 写入其中。

`LLM_STREAMING` 控制 CLI 是否实时输出 LLM 增量内容，设置为 `true`、`1`、`yes` 或 `on` 启用；未配置时默认为关闭。流式调用完成后仍会累积完整响应，供意图识别、Rewrite 等结构化解析使用。

```bash
conda run -n agent llm-verify "请用一句话问候我"
```

只想做一次 LLM 调用时，运行：

```bash
llm-once "请用一句话介绍你自己"
```

该命令会把时间和命令行工具定义一并传给模型，但只请求一次；如果模型返回工具调用，只展示调用内容，不执行工具，也不会自动发起第二次请求。

### 完整响应与工具调用示例

`llm-tools` 使用 Responses API，内置当前时间和受限的只读命令行工具。它会打印每一轮模型的完整响应 JSON、工具结果以及最终文本：

```bash
conda run -n agent llm-tools "请查询上海现在的时间，并告诉我"
```

命令行工具只允许 `pwd`、`ls`、`date`、`uname`、`whoami`、`echo` 和 Python 等简单命令，且不经过 shell，以免示例意外执行管道或重定向。

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

当前基础客户端和订单语义解析支持通过 `LLM_API_MODE` 在 Chat Completions 与 Responses API 间切换，并支持可配置的流式输出；暂不包含外部订单服务。

## SSE 工作流接口

新增 `POST /api/v2/chat`，返回 `text/event-stream`，事件包括 `THINKING_START`、`THINKING_STEP`、`THINKING_DONE`、`CREATE_ORDER_CONTEXT`、`DONE` 和 `ERROR`。本地使用 conda `agent` 环境启动：

```bash
conda run -n agent python -m pip install -e '.[dev]'
conda run -n agent inorder-api
```

请求示例：

```bash
curl -N -X POST http://localhost:8000/api/v2/chat \
  -H 'Accept: text/event-stream' -H 'Content-Type: application/json' \
  -d '{"session_id":"demo","message":"我要运一吨苹果从温州到上海"}'
```

启动 `inorder-api` 后也可以直接访问 `http://localhost:8000/` 打开内置测试前端。页面使用浏览器内存保存 `session_id`、`history` 和完整 `order_context`，通过 `fetch + SSE` 展示意图识别、订单处理、货物画像、车型处理及最终结果，适合连续测试“再加货物”“修改车型”等多轮输入。SSE 阶段会转换为“正在理解您的需求…”等面向用户的小提示，并在最终结果中展示订单摘要和待补充字段；刷新或点击“清空会话”会丢弃当前内存状态。

当 history 末尾存在未收到 assistant 回复的 user 消息时，API/CLI 会在入口自动识别为 pending turn：输入“重试”或“继续”会重放该消息，输入新的业务内容则与 pending 消息合并处理。成功响应的 SSE `DONE` 事件会返回恢复后的 `history`，客户端应使用它替换本地快照；失败时不伪造 assistant 回复，保留 pending 消息供后续重试。

订单工作流完成车型处理后会执行确定性的完整性检查。最小订单默认要求装货地、卸货地、货物名称、重量或数量至少一个以及送达时间；缺失时状态为 `incomplete`，`DONE` 结果会附带 `order_summary.missing_required` 和 `order_summary.next_prompt`。车型不作为默认必填字段，因为系统可以根据货物画像进行估算。

`reference_time` 是本次用户消息的时间锚点，格式为 `YYYY-MM-DD HH:MM`。调用方传入时优先使用；未传入时，Python 在 CLI 消息入口或 HTTP 请求入口按 `Asia/Shanghai` 当前时间生成一次。该值写入本次工作流 state，Rewrite、Extract 及格式修复重试均复用，不会在节点或重试中重新取时间。

多轮订单请求会将该时间锚点写入 `order_context.reference_time`。后续请求按 `order_context.reference_time`、请求级 `reference_time`、当前上海时间的顺序选择，已有上下文时间不会被新的请求值覆盖；调用方应将返回的完整 `order_context` 原样传回下一轮。

SSE 仅发送安全的工作流阶段和结构化结果，不发送 prompt、原始模型响应或隐藏推理；原有 `inorder` CLI 命令保持不变。

## 意图规划子图

意图识别阶段只输出计划，不执行订单业务。主意图只区分 `order` 与 `qa`：含明确订单执行请求即为 `order`，纯信息或操作方法询问为 `qa`；混合消息按「执行优先」归为 `order`。

```python
from inorder_llm.graph.intent import build_intent_graph

graph = build_intent_graph(your_intent_model)
result = graph.invoke({"message": "参考最近历史订单，修改当前草稿"})
plan = result["intent_plan"]
# plan.sub_intents: create_order / modify_draft
```

`IntentPlan` 支持主意图、多个订单子意图、步骤参数和 `depends_on`；后续主图可以根据该计划路由到业务子图。

图相关代码按职责位于 `inorder_llm/graph/`：

```text
graph/
├── base.py
├── main/
│   ├── state.py
│   ├── routing.py
│   └── graph.py
└── intent/
    ├── state.py
    ├── routing.py
    ├── graph.py
    └── nodes/
```

`main` 是父图，`intent` 和 `order` 是可独立运行或被父图挂载的子图。

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

`full` 链路现在通过 LangGraph MainGraph 编排 IntentGraph 和 OrderProcessingGraph：识别为 `order` 时进入 rewrite → extract → context update → cargo profile → vehicle resolution 订单处理子图；`intent` 和 `order` 可用于单独调试对应子图。当前 CLI 只做意图识别、订单语义解析和内存订单上下文更新，不执行历史订单查询、草稿修改、创建订单、确认下单或真实问答。

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
