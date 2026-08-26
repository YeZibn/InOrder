## MODIFIED Requirements

### Requirement: Extraction input parameters

extract 函数 SHALL 接受三个显式输入参数：`message`（用户本次输入）、`history`（对话历史，结构化消息列表，含 role 和 content）、`reference_time`（参考时间，格式 YYYY-MM-DD HH:MM）。传入的 `reference_time` SHALL 来自会话 `OrderContext` 已确定的时间锚点；函数不持有会话状态，不依赖全局可变状态。

#### Scenario: Extract with persisted reference time

- **WHEN** 调用 extract 函数并传入包含 `reference_time` 的订单上下文对应时间
- **THEN** 函数使用该值解析相对时间并返回带 action 的实体列表

#### Scenario: Empty history allowed

- **WHEN** 调用 extract 函数时 history 为空列表
- **THEN** 函数正常执行，输出不含 history context 的实体

#### Scenario: Reuse one reference time during extraction

- **WHEN** 同一次请求需要执行提取、结构化输出修复或重试
- **THEN** 所有调用复用会话已确定的 `reference_time`，不在节点或重试过程中重新生成
