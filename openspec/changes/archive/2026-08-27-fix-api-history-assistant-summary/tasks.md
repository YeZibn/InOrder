# Tasks: Fix API history assistant summary

## 1. 共享摘要提取函数

- [x] 1.1 新建共享函数：输入结构化 result（含 dataclass 对象），对带 `to_dict()` 的对象先转换，输出 assistant 摘要文本与基础 metadata；实现完整 fallback 次序（order_summary.user_message → intent 摘要 → 兜底文案）。
- [x] 1.2 单元测试：`OrderSummary` dataclass 对象在 result 中时提取 `user_message`；无 order_summary 时使用意图摘要素材；完全为空时兜底。

## 2. 接入两条路径

- [x] 2.1 `_with_recovery_history` 改为调用共享函数，assistant turn metadata 保持 `{"recovered": recovery.recovered}`。
- [x] 2.2 CLI `_assistant_summary` 改为共享函数的薄封装，保持现有输出文本与 metadata（含 chain 字段）逐字一致。
- [x] 2.3 API 层集成测试：DONE payload 中 assistant turn 内容等于订单总结 `user_message`，非 `"已完成意图识别"` 兜底文案。
- [x] 2.4 运行全量测试确认 CLI 与 API 均无回归。
