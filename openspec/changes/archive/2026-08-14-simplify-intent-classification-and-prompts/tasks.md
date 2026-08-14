## 1. 主意图两分类

- [x] 1.1 将主意图常量、状态类型和校验从 `order/qa/ambiguous` 改为 `order/qa`
- [x] 1.2 更新主意图节点，移除 ambiguous 判断和澄清字段写入
- [x] 1.3 更新 LangGraph 路由，删除 ambiguous 节点和分支

## 2. Prompt 打磨

- [x] 2.1 编写主意图 system prompt，明确 order/qa 定义、执行优先规则、边界示例和 JSON schema
- [x] 2.2 将主意图用户消息作为独立 user message 发送
- [x] 2.3 编写子意图 system prompt，明确多子意图、保守参数提取和 `depends_on` 规则
- [x] 2.4 保持结构化 JSON 解析和错误处理

## 3. 测试与文档

- [x] 3.1 更新主意图、图路由和澄清行为测试
- [x] 3.2 增加 prompt 内容和消息角色断言
- [x] 3.3 更新 README 和 CLI 相关示例
- [x] 3.4 在 conda `agent` 环境运行全量测试并验证 CLI
