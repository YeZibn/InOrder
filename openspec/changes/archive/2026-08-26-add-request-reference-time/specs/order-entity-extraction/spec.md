## MODIFIED Requirements

### Requirement: Extraction input parameters

extract 函数 SHALL 接受三个显式输入参数：`message`（用户本次输入）、`history`（对话历史，结构化消息列表，含 role 和 content）、`reference_time`（参考时间，格式 YYYY-MM-DD HH:MM）。`reference_time` SHALL 在用户消息进入请求边界时确定，并作为本次提取及其格式修复重试的稳定时间锚点；函数不持有会话状态，不依赖全局可变状态。

#### Scenario: Extract with all inputs
- **WHEN** 调用 extract 函数并传入 message、history 和 reference_time
- **THEN** 函数返回带 action 的实体列表，并使用传入的 reference_time 解析相对时间

#### Scenario: Empty history allowed
- **WHEN** 调用 extract 函数时 history 为空列表
- **THEN** 函数正常执行，输出不含 history context 的实体

#### Scenario: Request boundary supplies default reference time
- **WHEN** 用户消息进入 CLI 或 HTTP 请求且调用方未提供 reference_time
- **THEN** 请求边界生成当前 Asia/Shanghai 时间，并将非空的 YYYY-MM-DD HH:MM 值传入 extract

#### Scenario: Reuse one reference time during extraction
- **WHEN** 同一次请求需要执行提取、结构化输出修复或重试
- **THEN** 所有调用复用该请求已确定的 reference_time，不在节点或重试过程中重新生成
