## 1. Context models

- [x] 1.1 创建 `context/models.py`，实现 ConversationTurn、HistoryConversation、OrderContext、ConversationSession
- [x] 1.2 定义订单字段模型或稳定的字段类型别名，并实现 JSON-compatible `to_dict`
- [x] 1.3 创建 `context/__init__.py`，导出公共模型

## 2. Entity reducer

- [x] 2.1 创建 `context/reducer.py` 和 OrderContextReducer
- [x] 2.2 实现单值字段 set/replace/remove 规则
- [x] 2.3 实现 cargo 的 set/add/remove/replace 规则
- [x] 2.4 实现 vehicle_specs、remark 和其他集合/标量字段规则
- [x] 2.5 对未知实体类型和无法安全合并的数据定义明确行为

## 3. Tests and verification

- [x] 3.1 增加 HistoryConversation 和 ConversationSession 测试
- [x] 3.2 增加 OrderContext 序列化和空状态测试
- [x] 3.3 增加 reducer 的 set/add/remove/replace 全覆盖测试
- [x] 3.4 在 conda `agent` 环境运行全量测试并确认现有功能无回归
