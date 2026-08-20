## 1. Rewrite 契约

- [x] 1.1 更新 RewriteResult 模型和 resolver 校验，只保留 rewritten_text、extraction_text
- [x] 1.2 重写 rewrite prompt，要求歧义输入采用最佳努力上下文解释并生成可提取文本
- [x] 1.3 更新 rewrite 单元测试和 JSON fixture，移除澄清字段测试

## 2. 订单子图

- [x] 2.1 删除 OrderGraphState 的 rewrite 澄清字段及 route_rewrite、ClarificationNode
- [x] 2.2 将 LangGraph 固定连接 rewrite → extract → update_context
- [x] 2.3 更新订单子图测试，验证歧义 rewrite 仍调用 extractor，非法 JSON 仍报错

## 3. CLI 与规格

- [x] 3.1 移除 runner 和 CLI 的澄清/Extract 跳过状态与输出
- [x] 3.2 更新 CLI、订单子图和 rewrite 相关测试
- [x] 3.3 更新 prompt changelog，运行完整测试并同步规格
