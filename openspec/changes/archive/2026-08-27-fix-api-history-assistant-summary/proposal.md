# Fix API history assistant summary

## Why

`/api/v2/chat` 的 DONE 事件通过 `_with_recovery_history` 构建会话历史快照，但该函数直接对 `order_summary` 做 `isinstance(dict)` 判断——而 workflow state 里的 `order_summary` 是 `OrderSummary` dataclass 对象而非 dict。类型判断静默失败后掉进 fallback，assistant 历史被写成 `"已完成意图识别：order"`：

- 完整的订单总结（`user_message`："目前已为您识别出：温州到上海，货物为苹果…"）没有进入历史。
- 多轮对话质量下降：下一条用户消息的 LLM 上下文只知道"意图是 order"，丢失全部已识别订单细节。
- CLI 路径（`_assistant_summary`）有 `_data()` 的 `to_dict()` 转换，行为正确；API 与 CLI 是同一逻辑的两份平行实现且已经漂移。

## What Changes

- 修复 `_with_recovery_history`：对 `OrderSummary` 等带 `to_dict()` 的对象先转换再取字段，使 DONE 历史的 assistant turn 使用 `order_summary.user_message`（与 Web UI 展示给用户的最终总结一致）。
- 将"从结构化结果提取 assistant 摘要文本"收敛为共享函数，CLI 与 API 复用同一实现，消除平行实现漂移（遵循项目"避免平行实现"教训）。
- 不改变 DONE 事件帧格式与 `history_recovered` 字段语义。

## Capabilities

### Modified

- `workflow-sse-events`: DONE 返回的历史快照中 assistant turn 内容 SHALL 来自订单最终总结（`order_summary.user_message`），fallback 仅在无任何可提取摘要时使用。
