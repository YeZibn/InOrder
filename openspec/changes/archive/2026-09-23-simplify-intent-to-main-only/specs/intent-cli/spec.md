## MODIFIED Requirements

### Requirement: Mode to graph routing

系统 SHALL 将当前链路映射到明确处理入口：`intent` 调用仅包含主意图分类的意图图，`order` 调用订单处理子图，`full` 只调用 LangGraph MainGraph，由其根据 `main_intent` 路由到订单或 QA 分支。CLI 不得在缺少 MainGraph 时改用 IntentRunner 与 OrderRunner 实现另一套 full 编排；缺少 MainGraph 时 SHALL 给出明确的配置不可用反馈。旧的 `auto`、`qa`、`plan` 模式不再作为三条链路的主选择项。CLI 不再依赖子意图计划进行展示或路由。

#### Scenario: Intent chain
- **WHEN** 当前链路为 `intent` 且用户输入普通消息
- **THEN** 系统调用意图图并输出 `main_intent` 与置信度

#### Scenario: Order chain
- **WHEN** 当前链路为 `order` 且用户输入普通消息
- **THEN** 系统调用订单处理子图并输出订单解析结果

#### Scenario: Full chain
- **WHEN** 当前链路为 `full` 且用户输入普通消息
- **THEN** 系统按 `main_intent` 决定是否继续调用订单处理子图

#### Scenario: Full chain uses MainGraph as its only orchestrator
- **WHEN** 当前链路为 `full` 且已配置 MainGraph
- **THEN** 系统调用 MainGraph 处理并路由请求，不通过 CLI runner 重新串联意图图和订单图

#### Scenario: Full chain without MainGraph
- **WHEN** 当前链路为 `full` 且未配置 MainGraph
- **THEN** 系统返回明确的配置不可用反馈，且不回退到 IntentRunner 与 OrderRunner 的顺序调用

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

CLI 的意图链路 SHALL 只展示主意图识别结果和链路状态，不展示或执行子意图步骤，不执行订单查询、草稿修改、订单创建、确认下单或真实问答回答。

#### Scenario: Intent output has no sub-intents
- **WHEN** 用户在意图链路输入订单相关消息
- **THEN** CLI 输出主意图分类结果，不输出 `sub_intents` 或 `depends_on`

#### Scenario: Order message in CLI
- **WHEN** 用户在任意模式输入订单相关消息
- **THEN** CLI 仅按当前链路执行既定识别或订单解析流程，不因意图识别阶段产生业务副作用
