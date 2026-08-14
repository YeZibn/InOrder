## Context

项目已有 `build_intent_graph` 编译入口和 IntentPlan 模型，但目前只有面向开发者的 Python 调用方式。该 change 增加交互式 CLI，不改变图内部业务边界。行为契约见 specs/intent-cli/spec.md。

## Goals / Non-Goals

**Goals:**

- 提供可测试的命令解析和交互 session。
- 通过 `/intent` 切换 `auto/order/qa/plan` 模式。
- 将普通消息路由到现有 compiled graph 或明确的占位入口。
- 统一输出模式、IntentPlan、澄清和错误信息。

**Non-Goals:**

- 不实现订单服务、问答服务、持久化、认证或多用户会话。
- 不实现真实交互式终端 UI 框架、补全、历史搜索或流式输出。
- 不改变 LangGraph 节点和订单意图模型的业务契约。

## Decisions

### 使用标准输入循环而非终端 UI 框架

第一版使用 Python 标准输入输出，避免引入 Rich、Typer 或 prompt toolkit 等额外复杂度；命令解析和 session 可以独立测试，未来再替换 UI 层。

### 将命令解析与模式路由分离

```text
raw line
  ├── slash command → CommandParser → Session update
  └── ordinary text → ModeRouter → Graph adapter → Formatter
```

这样 `/intent` 的交互逻辑不会和 LangGraph 节点耦合。

### 四种模式的边界

- `auto`：调用完整 compiled intent graph。
- `order`：当前骨架中仍通过 intent graph 识别订单计划，但要求主意图为 order；不执行订单。
- `qa`：返回明确的“问答入口尚未实现”占位结果。
- `plan`：调用完整 graph，并打印结构化 IntentPlan。

### Session 使用可替换 IO

Session 接受 input/output 函数，测试可以注入列表读取器和缓冲输出器，不依赖真实终端。

## Risks / Trade-offs

- [真实 LLM 调用依赖配置和网络] → CLI 支持注入 graph/model，测试完全使用 mock。
- [order/qa 模式可能让用户误以为业务已执行] → 输出明确标记“识别-only，未执行业务”。
- [会话上下文无限增长] → 第一版 `/clear` 仅清理本地消息；持久化和裁剪后续再设计。

## Migration Plan

增加 `inorder` 命令入口，不影响现有 `llm-verify`。开发者可以继续直接调用 graph builder；CLI 稳定后再考虑默认入口和安装文档调整。

## Open Questions

无。后续可单独决定终端美化、持久化和真实 QA graph。
