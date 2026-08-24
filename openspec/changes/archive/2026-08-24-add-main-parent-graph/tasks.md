## 1. 父图状态与基础结构

- [x] 1.1 新增 MainGraphState，定义输入上下文、意图结果、订单结果和兼容输出字段。
- [x] 1.2 新增 MainGraph、父图节点和 main_intent 路由函数。
- [x] 1.3 将现有 IntentGraph 和 OrderProcessingGraph 作为 LangGraph 子图挂载到父图。

## 2. 父子图状态与结果汇总

- [x] 2.1 实现意图子图输入映射和输出合并，不改变意图图独立调用行为。
- [x] 2.2 实现订单子图输入映射和输出合并，传递 history、order_context、reference_time。
- [x] 2.3 实现 QA 终止分支和 order 分支的兼容结果包装。
- [x] 2.4 确保子图异常向上暴露，不生成部分成功结果。

## 3. CLI 接入

- [x] 3.1 修改 FullChainRunner/启动入口，使 full 链路调用 MainGraph。
- [x] 3.2 保留 intent、order 独立链路和现有 CLI 输出、session context 更新行为。
- [x] 3.3 更新 README 和相关 graph 导出，说明父图与子图关系。

## 4. 测试与验证

- [x] 4.1 增加父图 order 路由和子图调用顺序测试。
- [x] 4.2 增加父图 qa 分支不调用订单子图测试。
- [x] 4.3 增加父子图状态传递、结果包装和异常传播测试。
- [x] 4.4 运行 conda `agent` 环境完整测试集并验证 CLI 三条链路。
