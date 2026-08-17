## 1. Order graph foundation

- [x] 1.1 创建 `graph/order/` 包、状态类型和公开构建入口
- [x] 1.2 定义 rewrite model 与 extractor 的最小注入协议
- [x] 1.3 创建 rewrite、澄清路由、extract、finalize 节点并编译 StateGraph

## 2. Node behavior

- [x] 2.1 rewrite 节点读取 message、reference_time、history 和 order_context
- [x] 2.2 澄清路由在 `needs_clarification=true` 时跳过 extract
- [x] 2.3 extract 节点使用 rewrite 的 `extraction_text`，并传递 reference_time/history
- [x] 2.4 finalize 节点返回 rewrite_result、entities、澄清状态且不修改上下文

## 3. Tests and boundaries

- [x] 3.1 覆盖成功路径：rewrite 后 extract 返回实体
- [x] 3.2 覆盖澄清路径：extract 未被调用且实体为空
- [x] 3.3 覆盖历史、订单上下文和参考时间的参数传递
- [x] 3.4 覆盖 rewrite/extract 非法结构化输出错误传播
- [x] 3.5 使用 conda `agent` 环境运行完整测试，确认现有主意图图和 reducer 行为不变
