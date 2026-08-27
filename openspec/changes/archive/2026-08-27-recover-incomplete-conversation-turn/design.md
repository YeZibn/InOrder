## Context

当前 CLI 在工作流调用前追加 user 消息，异常时不追加 assistant；API 则由调用方传入 history，服务端只输出 SSE，不持久化会话。恢复逻辑需要位于 API/CLI 入口，而不是 Rewrite 或 LangGraph 业务节点。

## Goals / Non-Goals

**Goals:**

- 统一识别 pending user 回合并生成一次性的工作流输入。
- 支持新消息补充和重试控制词两种恢复模式。
- 通过 DONE 返回可替换的 history 快照或 patch。

**Non-Goals:**

- 不推断服务端是否已经产生外部业务副作用。
- 不实现数据库持久化、跨进程 session 存储或真正下单幂等。

## Decisions

1. **入口层恢复**：新增纯函数恢复器，输入 history 与当前 message，输出规范化 history、工作流 message 和恢复标记。这样业务图保持无状态，也避免 Rewrite 重复处理悬空消息。
2. **连续 user 合并**：定位最后一个 assistant 之后的 user 消息块；控制词重试时只取该块，普通消息按换行拼接。完全相同的当前输入去重。
3. **成功后回写**：工作流成功生成摘要后，将合并后的 user 回合和 assistant 摘要组成新 history；DONE 同时提供 `history` 或 `history_patch`，客户端可覆盖本地快照。
4. **失败保留 pending**：入口不在 ERROR 路径追加 assistant；网络断开时调用方继续保存原 pending history。由于 Python 侧当前无外部副作用，允许后续重放；未来接入副作用时增加 request id 幂等。

## Risks / Trade-offs

- [服务已执行但响应丢失导致重复执行] → 当前解析流程无外部副作用；未来业务执行前引入 request id。
- [用户输入“继续”本身可能是业务语义] → 仅在检测到 pending turn 时将明确控制词视为重试，否则按普通消息处理。
- [多条连续 user 消息缺少边界] → 按最后一个 assistant 后的连续块合并，并保留原始顺序。

## Migration Plan

先实现恢复器和 API/CLI 接入，再更新 SSE/前端 history 回写与测试；旧客户端未消费 history_patch 时仍可继续使用原 DONE 结果。回滚时移除入口恢复调用即可。
