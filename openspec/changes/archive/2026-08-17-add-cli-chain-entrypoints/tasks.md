## 1. Chain runner foundation

- [x] 1.1 定义 `full`、`intent`、`order` 链路枚举和 CLI session 上下文
- [x] 1.2 创建意图、下单和完整链路 runner 适配层
- [x] 1.3 组装 LLM client、意图图和订单处理子图的默认入口

## 2. CLI commands and routing

- [x] 2.1 新增 `/chain` 直接切换和交互式选择
- [x] 2.2 保留 `/intent` 兼容命令并更新 `/mode`、`/help` 输出
- [x] 2.3 将普通消息路由到当前链路并格式化三类结果
- [x] 2.4 为 full 链路实现 qa 跳过订单子图、order 继续订单子图的条件组合
- [x] 2.5 暴露 full/order 订单处理阶段状态，区分 extract 已执行与澄清跳过

## 3. Session context and tests

- [x] 3.1 为 order/full 链路传递 HistoryConversation、OrderContext 和 reference_time
- [x] 3.2 `/clear` 清空消息、历史和订单上下文但保留当前链路
- [x] 3.3 覆盖三条链路的 runner 调用顺序和输出
- [x] 3.4 覆盖命令兼容、非法链路和上下文传递
- [x] 3.5 更新 README 并使用 conda `agent` 环境运行完整测试
- [x] 3.6 增加 full 链路成功提取和澄清跳过的阶段状态测试
