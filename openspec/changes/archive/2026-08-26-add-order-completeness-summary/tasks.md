## 1. Completeness domain model and rules

- [x] 1.1 定义订单摘要、缺失字段和完整性状态的数据模型及序列化契约
- [x] 1.2 实现 pickup/dropoff、货物名称、重量或数量、delivery_time 的确定性校验规则
- [x] 1.3 实现事实摘要和补充提示模板，确保车型缺失不被默认判为必填

## 2. Order graph integration

- [x] 2.1 新增订单完整性检查节点，并将其连接为车型处理之后的最后一个节点
- [x] 2.2 将 `order_summary` 返回到订单子图和 MainGraph，同时保留现有结构化字段
- [x] 2.3 覆盖完整订单、缺少时间、缺少重量/数量和不完整地址等场景测试

## 3. Output consumers

- [x] 3.1 更新 CLI 最终输出，优先展示业务摘要和缺失字段提示，隐藏内部 Rewrite/Extract 细节
- [x] 3.2 更新 SSE `DONE` payload 和前端最终结果展示，兼容非订单分支
- [x] 3.3 确保 HistoryConversation 只保存精简摘要，不写入完整上下文或调试数据

## 4. Verification and documentation

- [x] 4.1 增加摘要契约、规则边界和输出兼容性测试
- [x] 4.2 更新 API/CLI 文档说明订单完整性状态和补充提示
- [x] 4.3 运行完整测试集与 OpenSpec 严格校验

## 5. User-facing wording refinement

- [x] 5.1 在摘要契约中增加 `user_message`，将结构化状态与用户展示文案分离
- [x] 5.2 为完整订单和信息不足订单编写自然、礼貌、可继续对话的回复模板
- [x] 5.3 让 CLI、SSE 客户端和 Web 最终回复优先展示 `user_message`，禁止直接显示内部字段名或原始 JSON
- [x] 5.4 增加用户视角文案测试，覆盖已识别内容、缺失时间提示和输入示例
- [x] 5.5 运行完整测试集与 OpenSpec 严格校验

## 6. Main conversation summary display

- [x] 6.1 更新 Web `DONE` 事件处理，在主对话框追加 `user_message` 助手气泡，同时保留右侧摘要和结构化结果展示
- [x] 6.2 覆盖订单摘要、顶层摘要兼容路径、无摘要响应和重复 `DONE` 的前端展示行为测试
- [x] 6.3 运行前端/SSE 相关测试与 OpenSpec 严格校验
