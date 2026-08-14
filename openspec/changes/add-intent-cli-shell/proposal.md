## Why

当前项目已有 LLM 客户端和编译后的意图识别 LangGraph，但缺少一个可直接使用和调试的交互入口。需要先提供轻量 CLI shell，让用户通过 `/intent` 选择当前对话模式，并将普通消息路由到对应的意图图入口。

## What Changes

- 新增交互式 CLI shell，支持持续输入普通消息和斜杠命令。
- 支持 `/intent` 交互选择模式，以及 `/intent <mode>` 直接切换模式。
- 第一阶段提供 `auto`、`order`、`qa`、`plan` 四种模式。
- 支持 `/mode`、`/help`、`/clear`、`/exit` 基础命令。
- 维护当前模式、消息上下文和 graph 调用适配。
- 统一格式化 IntentPlan、澄清状态和错误输出。
- 本阶段不执行订单业务、不回答问答、不持久化会话、不实现流式输出或 checkpoint。

## Capabilities

### New Capabilities

- `intent-cli`: 提供交互式 CLI shell、模式切换和意图图调用入口。

### Modified Capabilities

无。

## Impact

- 新增 CLI session、命令解析、模式路由和输出格式化模块。
- 新增项目命令入口 `inorder`。
- 复用现有 LangGraph intent graph；不修改订单或问答业务（当前尚未实现）。
