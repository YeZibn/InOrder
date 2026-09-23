# intent-cli Specification

## Purpose
为用户提供一个可交互的命令行入口，通过斜杠命令选择意图模式并调用现有 LangGraph 意图图，便于后续对话式业务开发与调试。
## Requirements
### Requirement: Interactive CLI session

系统 SHALL 提供持续读取用户输入的交互式 CLI session，并区分斜杠命令和普通对话消息。

#### Scenario: Start interactive session
- **WHEN** 用户启动 `inorder` 命令
- **THEN** 系统显示当前模式并等待用户输入

#### Scenario: Process ordinary message
- **WHEN** 用户输入非斜杠开头的消息
- **THEN** 系统将消息交给当前模式对应的 graph 入口并输出统一结果

### Requirement: Intent mode selection

系统 SHALL 支持通过 `/chain [full|intent|order]` 选择运行链路，并保留 `/intent` 作为切换到 `intent` 链路的兼容命令；当前 CLI 状态 SHALL 显示所选链路。

#### Scenario: Direct chain switch

- **WHEN** 用户输入 `/chain order`
- **THEN** 系统将当前链路切换为 `order` 并反馈新链路

#### Scenario: Direct mode switch

- **WHEN** 用户输入 `/intent order`
- **THEN** 系统将当前模式切换为 `order` 并反馈新模式

#### Scenario: Interactive chain switch

- **WHEN** 用户输入不带参数的 `/chain`
- **THEN** 系统展示 `full`、`intent`、`order` 可选链路并根据用户选择切换

#### Scenario: Interactive mode switch

- **WHEN** 用户输入不带参数的 `/intent`
- **THEN** 系统展示可选模式并根据用户选择切换模式

#### Scenario: Legacy intent alias

- **WHEN** 用户输入 `/intent`
- **THEN** 系统保留兼容行为并切换或提示 `intent` 链路

#### Scenario: Invalid chain

- **WHEN** 用户输入未支持的链路
- **THEN** 系统拒绝切换并提示合法链路

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

系统 SHALL 将当前链路映射到明确处理入口：`intent` 调用仅进行主意图分类的意图图，`order` 调用订单处理子图，`full` 只调用 LangGraph MainGraph，由 MainGraph 根据 `main_intent` 路由到订单或 QA 分支。CLI 不得在缺少 MainGraph 时改为顺序调用意图图和订单图；此时 SHALL 给出明确的配置不可用反馈。旧的 `auto`、`qa`、`plan` 模式不再作为三条链路的主选择项。

#### Scenario: Intent chain

- **WHEN** 当前链路为 `intent` 且用户输入普通消息
- **THEN** 系统调用意图图并输出 `main_intent` 与可选置信度

#### Scenario: Order chain

- **WHEN** 当前链路为 `order` 且用户输入普通消息
- **THEN** 系统调用订单处理子图并输出订单解析结果

#### Scenario: Full chain

- **WHEN** 当前链路为 `full` 且用户输入普通消息
- **THEN** 系统按主意图结果决定是否继续调用订单处理子图

#### Scenario: Full chain uses MainGraph as its only orchestrator
- **WHEN** 当前链路为 `full` 且已配置 MainGraph
- **THEN** 系统调用 MainGraph 处理并路由请求，不由 CLI runner 另行串联意图图和订单图

#### Scenario: Full chain without MainGraph
- **WHEN** 当前链路为 `full` 且未配置 MainGraph
- **THEN** 系统返回明确的配置不可用反馈，且不回退到意图图与订单图的顺序调用

#### Scenario: Full chain exposes order processing status

- **WHEN** full 链路进入订单处理子图
- **THEN** 系统输出订单处理是否进入、rewrite 是否完成、extract 是否执行或跳过、跳过原因和实体数量

#### Scenario: Full chain displays the QA terminal result
- **WHEN** full 链路的 MainGraph 将请求路由到 QA 终态
- **THEN** 系统不进入订单处理子图，并展示 QA 占位结果而不是订单分支未进入的提示

#### Scenario: Auto mode

- **WHEN** 当前模式为 `auto` 且用户输入普通消息
- **THEN** 系统调用完整链路

#### Scenario: Plan mode

- **WHEN** 当前模式为 `plan` 且用户输入普通消息
- **THEN** 系统输出结构化意图计划

### Requirement: Safe recognition-only behavior

CLI 的 `intent` 链路 SHALL 只展示主意图分类结果和链路状态，不展示子意图步骤。`order` 和 `full` 链路可以执行订单语义解析，但 CLI SHALL 不执行历史订单查询、草稿修改、订单创建、确认下单或真实问答回答。

#### Scenario: Intent output has no sub-intents
- **WHEN** 用户在意图链路输入订单相关消息
- **THEN** CLI 输出主意图分类结果，不输出 `sub_intents` 或 `depends_on`

#### Scenario: Order message in CLI
- **WHEN** 用户在任意模式输入订单相关消息
- **THEN** CLI 按当前链路执行意图识别或订单语义解析，不产生历史查询、草稿修改、订单创建或确认下单等业务副作用
