## 1. LangGraph 依赖与状态

- [x] 1.1 在 Python 项目依赖中加入 LangGraph，并在 conda `agent` 环境确认兼容版本。
- [x] 1.2 定义 TypedDict 图状态，覆盖消息、主意图、子意图、计划和澄清字段。

## 2. 独立节点与路由

- [x] 2.1 实现独立的 `main_intent_node`，只负责主意图识别。
- [x] 2.2 实现独立的 `sub_intent_node`，只在 `order` 路由下执行多子意图识别。
- [x] 2.3 实现计划构建、计划校验、澄清和统一 finalize 节点。
- [x] 2.4 实现 `order / qa / ambiguous` 条件路由函数和 StateGraph 边。

## 3. Graph Builder 与兼容层

- [x] 3.1 实现 graph builder，返回编译后的 LangGraph graph。
- [x] 3.2 复用现有 IntentPlan 和校验逻辑，保持识别-only，不注入业务工具。
- [x] 3.3 明确旧 facade 与新 compiled graph 的入口关系，并更新使用说明。

## 4. 测试与验证

- [x] 4.1 编写 graph 编译和 order 路由测试，验证两个识别节点均执行。
- [x] 4.2 编写 qa 路由测试，验证跳过子意图节点并返回统一状态。
- [x] 4.3 编写 ambiguous 路由测试，验证进入澄清节点且不执行子意图节点。
- [x] 4.4 编写 recognition-only 副作用隔离测试。
- [x] 4.5 在 conda `agent` 环境运行完整测试、编译和 OpenSpec 校验。

## 5. 范围确认

- [x] 5.1 确认本阶段未实现订单查询、草稿修改、订单创建、确认下单或问答回答。
- [x] 5.2 确认 checkpoint、interrupt、流式执行和并行分支留待后续 change。
