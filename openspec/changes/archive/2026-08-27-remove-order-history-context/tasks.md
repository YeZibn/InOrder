## 1. Remove history context from time processing

- [x] 1.1 删除时间归一化中的 `new_order/history` 校验和输出字段，仅保留 start/end/kind/timezone/raw
- [x] 1.2 删除 Reducer 对 history 时间的特殊分支，并让当前订单时间实体正常更新 delivery_time
- [x] 1.3 更新订单摘要的送达时间有效性判断，不再读取时间 context

## 2. Remove historical-order domain contracts

- [x] 2.1 从 `OrderContext`、Reducer 和 API 上下文映射中删除 `referenced_order_id`/`order_id`
- [x] 2.2 从意图 Prompt、校验和模型测试中删除 `query_history_order`，仅保留当前订单创建与修改
- [x] 2.3 从 Extract Prompt、LangExtract examples、实体类型契约中删除历史订单实体和历史时间语义
- [x] 2.4 更新 Rewrite Prompt，禁止历史订单恢复或查询，同时保留当前会话 HistoryConversation 的多轮指代能力

## 3. Update supporting matching and documentation

- [x] 3.1 将车型匹配数据集中的 `historical_reference` 归类改为 `unresolved_reference`
- [x] 3.2 更新 README、API/CLI 说明和 Prompt changelog，区分会话历史与历史订单
- [x] 3.3 同步主 OpenSpec 规格，移除历史订单要求并补充无 context 时间契约

## 4. Tests and verification

- [x] 4.1 删除或改写 history 时间、order_id、query_history_order 相关测试
- [x] 4.2 增加“明天下午三点”无 context 时间抽取、归一化和 Reducer 更新测试
- [x] 4.3 增加当前会话 HistoryConversation 多轮改写回归测试，确保未误删会话历史
- [x] 4.4 运行全量测试、前端/SSE 测试和 OpenSpec 严格校验
