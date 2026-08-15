## 1. Rewrite domain model

- [x] 1.1 创建 `rewrite/models.py`，实现 RewriteResult 及稳定序列化
- [x] 1.2 创建 `rewrite/__init__.py`，导出公共 API

## 2. Rewrite resolver and prompt

- [x] 2.1 创建 `rewrite/resolver.py`，实现 system prompt、上下文格式化和 LLM 调用
- [x] 2.2 使用独立 system/user 消息传递规则、OrderContext、HistoryConversation 和本轮输入
- [x] 2.3 实现严格 JSON 解析和必需字段校验，复用结构化错误边界
- [x] 2.4 确保 resolver 不修改输入上下文、不接触业务工具

## 3. Tests, changelog and verification

- [x] 3.1 增加 RewriteResult 序列化和非法输出测试
- [x] 3.2 增加增量 cargo、地址替换、删除和歧义场景测试
- [x] 3.3 增加消息角色、上下文分区和 prompt 内容断言
- [x] 3.4 使用 `$prompt-changelog` 追加 prompt 变更记录
- [x] 3.5 在 conda `agent` 环境运行全量测试
