# Design: Fix API history assistant summary

## Context

DONE 事件的历史快照构建存在两条平行实现：

```
CLI (cli/app.py _assistant_summary)      API (workflow/api.py _with_recovery_history)
├── _data() → to_dict() 转换 ✓           ├── isinstance(dict) 直接判断 ✗
├── order_summary.user_message 入历史     ├── 类型判断失败 → fallback
└── fallback: "订单已解析"                └── fallback: "已完成意图识别：order"
```

`OrderCompletenessNode.run()` 返回的 `order_summary` 是 `OrderSummary` dataclass（`to_dict()` 提供 JSON 兼容视图），state 与 DONE payload 全程保持对象形态，仅在客户端序列化时转 dict。API 路径在服务端消费时漏掉了这一转换。

## Goals / Non-Goals

- Goals: DONE 历史 assistant turn 内容正确（订单最终总结）；摘要提取逻辑单一来源。
- Non-Goals: 不改变 SSE 帧格式、history 字段结构、recovery 语义；不动 CLI 展示逻辑。

## Decisions

1. **收敛共享函数。** 在 CLI 与 API 都可达的位置新建共享摘要提取函数（放 `cli/app.py` 会造成 workflow 反向依赖 cli，不合理；放在 `workflow/` 或中立模块，由两侧导入）。函数职责：输入结构化 result dict（含 dataclass 对象），输出 `(assistant_text, metadata_dict)`。
2. **统一 `_data()` 转换语义。** 共享函数内部对一切带 `to_dict()` 的对象先转换再取字段，覆盖 `OrderSummary`、intent result 等。
3. **保持各入口 metadata 差异。** CLI 的 metadata 含 `chain` 等字段，API 的 assistant turn metadata 为 `{"recovered": ...}`——共享函数只负责文本提取与基础 metadata 组装，调用方补充各自特有字段。
4. **fallback 次序不变。** 有 `order_summary` 用 `user_message`；无则意图摘要素材；仅当完全无可提取内容时使用简短兜底文案。

## Risks / Trade-offs

- [CLI 与 API 迁移到共享函数后行为细微变化] → 以现有测试为基线：CLI 输出文本保持逐字一致；API 的 DONE history 断言新增。
- [`OrderSummary` 未来增加字段] → 共享函数只读 `user_message`/`summary`，不受新增字段影响。

## Migration Plan

先落共享函数与其单测 → API `_with_recovery_history` 改为调用共享函数并补 `{"recovered": ...}` → CLI `_assistant_summary` 改为薄封装 → 跑全量测试确认无回归。

## Open Questions

- 无。
