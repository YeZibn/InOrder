## MODIFIED Requirements

### Requirement: Consume and display SSE workflow events

页面 SHALL 使用 POST 请求消费 `/api/v2/chat` 的 SSE 流，并按到达顺序展示公开工作流事件及子图节点完成进度，不暴露 prompt、原始模型响应或内部堆栈。

#### Scenario: Display workflow stages

- **WHEN** 服务端发送 `THINKING_START`、`THINKING_STEP` 或节点级完成事件
- **THEN** 页面在当前消息的处理中区域立即追加对应的用户友好阶段或节点进度提示

### Requirement: Show friendly real-time progress hints

页面 SHALL 在 SSE 事件到达后立即将阶段和节点完成事件适配为面向用户的简短、友好的处理提示，并按事件顺序维护可读记录；不得直接向用户展示事件名、内部节点名、prompt 或完整 SSE JSON。

#### Scenario: Start processing hint

- **WHEN** 服务端发送 `THINKING_START`
- **THEN** 页面立即显示“正在理解您的需求…”或语义等价的开始处理提示

#### Scenario: Stage-specific hints

- **WHEN** 服务端发送带有 `stage` 的 `THINKING_STEP`
- **THEN** 页面根据公开阶段显示对应的用户提示，例如意图阶段显示“正在识别您的运输需求…”，订单阶段显示“正在整理订单信息…”，货物画像阶段显示“正在分析货物特征…”，车型阶段显示“正在匹配合适车型…”

#### Scenario: Append repeated order-node hints

- **WHEN** 订单子图的多个节点依次完成，即使它们属于同一公开业务阶段
- **THEN** 页面仍逐条追加不同的完成提示，不因阶段名称相同而折叠或覆盖之前的记录

#### Scenario: Keep terminal and error behavior

- **WHEN** 页面收到 `THINKING_DONE`、`DONE` 或 `ERROR`
- **THEN** 页面分别显示完成或错误提示并结束加载状态，错误时不伪造成功结果

#### Scenario: Context update hint

- **WHEN** 服务端发送 `CREATE_ORDER_CONTEXT`
- **THEN** 页面显示“订单信息已更新”或语义等价提示，并同步刷新上下文面板

#### Scenario: Finish processing hint

- **WHEN** 服务端发送 `THINKING_DONE` 或 `DONE`
- **THEN** 页面显示“处理完成”提示；收到 `DONE` 后再展示最终结构化结果

#### Scenario: Error hint

- **WHEN** 服务端发送 `ERROR`
- **THEN** 页面将错误 payload 适配为简明错误提示、结束加载状态，并不显示成功完成提示

#### Scenario: Display context update

- **WHEN** 服务端发送 `CREATE_ORDER_CONTEXT`
- **THEN** 页面更新内存中的 `order_context`，并刷新上下文 JSON 视图

#### Scenario: Display terminal result

- **WHEN** 服务端发送 `DONE`
- **THEN** 页面展示安全的最终结构化结果并结束当前消息的加载状态

#### Scenario: Display normalized error

- **WHEN** 服务端发送 `ERROR`
- **THEN** 页面展示错误消息和阶段，并结束当前消息的加载状态，不伪造成功结果
