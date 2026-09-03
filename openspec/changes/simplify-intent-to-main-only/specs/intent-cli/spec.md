## MODIFIED Requirements

### Requirement: Mode to graph routing

系统 SHALL 将当前链路映射到明确处理入口：`intent` 调用仅包含主意图分类的意图图，`order` 调用订单处理子图，`full` 先读取 `main_intent` 再决定是否继续调用订单处理子图；CLI 不再依赖子意图计划进行展示或路由。

#### Scenario: Intent chain
- **WHEN** 当前链路为 `intent` 且用户输入普通消息
- **THEN** 系统调用意图图并输出 `main_intent` 与置信度

#### Scenario: Full chain
- **WHEN** 当前链路为 `full` 且用户输入普通消息
- **THEN** 系统按 `main_intent` 决定是否继续调用订单处理子图

### Requirement: Safe recognition-only behavior

CLI 的意图链路 SHALL 只展示主意图识别结果和链路状态，不展示或执行子意图步骤，不执行订单查询、草稿修改、订单创建、确认下单或真实问答回答。

#### Scenario: Intent output has no sub-intents
- **WHEN** 用户在意图链路输入订单相关消息
- **THEN** CLI 输出主意图分类结果，不输出 `sub_intents` 或 `depends_on`

#### Scenario: Order message in CLI
- **WHEN** 用户在任意模式输入订单相关消息
- **THEN** CLI 仅按当前链路执行既定识别或订单解析流程，不因意图识别阶段产生业务副作用
