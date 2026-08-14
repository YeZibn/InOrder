## Purpose

为用户提供一个可交互的命令行入口，通过斜杠命令选择意图模式并调用现有 LangGraph 意图图，便于后续对话式业务开发与调试。

## ADDED Requirements

### Requirement: Interactive CLI session

系统 SHALL 提供持续读取用户输入的交互式 CLI session，并区分斜杠命令和普通对话消息。

#### Scenario: Start interactive session
- **WHEN** 用户启动 `inorder` 命令
- **THEN** 系统显示当前模式并等待用户输入

#### Scenario: Process ordinary message
- **WHEN** 用户输入非斜杠开头的消息
- **THEN** 系统将消息交给当前模式对应的 graph 入口并输出统一结果

### Requirement: Intent mode selection

系统 SHALL 支持 `auto`、`order`、`qa` 和 `plan` 四种模式，并支持 `/intent` 交互选择及 `/intent <mode>` 直接切换。

#### Scenario: Direct mode switch
- **WHEN** 用户输入 `/intent order`
- **THEN** 系统将当前模式切换为 `order` 并反馈新模式

#### Scenario: Interactive mode switch
- **WHEN** 用户输入不带参数的 `/intent`
- **THEN** 系统展示可选模式并根据用户选择切换模式

#### Scenario: Invalid mode
- **WHEN** 用户输入未支持的模式
- **THEN** 系统拒绝切换并提示合法模式

### Requirement: Built-in commands

系统 SHALL 支持 `/mode`、`/help`、`/clear` 和 `/exit` 命令。

#### Scenario: Show current mode
- **WHEN** 用户输入 `/mode`
- **THEN** 系统显示当前模式

#### Scenario: Clear session
- **WHEN** 用户输入 `/clear`
- **THEN** 系统清空当前消息上下文但保留 CLI 运行

#### Scenario: Exit session
- **WHEN** 用户输入 `/exit`
- **THEN** 系统结束交互并正常退出

### Requirement: Mode to graph routing

系统 SHALL 将四种模式映射到明确的处理入口：`auto` 调用完整意图图，`order` 调用订单子意图识别入口，`qa` 返回问答模式占位结果，`plan` 调用意图图并输出结构化计划。

#### Scenario: Auto mode
- **WHEN** 当前模式为 `auto` 且用户输入普通消息
- **THEN** 系统调用编译后的意图图

#### Scenario: Plan mode
- **WHEN** 当前模式为 `plan` 且用户输入普通消息
- **THEN** 系统输出可读的 IntentPlan 字段

### Requirement: Safe recognition-only behavior

CLI SHALL 只展示意图识别结果和模式状态，不执行订单查询、草稿修改、订单创建、确认下单或真实问答回答。

#### Scenario: Order message in CLI
- **WHEN** 用户在任意模式输入订单相关消息
- **THEN** CLI 只输出识别计划，不产生业务数据副作用
