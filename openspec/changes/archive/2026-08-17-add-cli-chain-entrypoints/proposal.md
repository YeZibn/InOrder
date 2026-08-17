## Why

当前 CLI 只有意图识别模式，无法分别调试完整链路、意图链路和下单语义解析链路。增加明确的链路入口后，可以在同一个交互会话中独立验证主意图图、订单处理子图以及两者的组合行为。

## What Changes

- 将 CLI 运行入口统一为 `full`、`intent`、`order` 三条链路。
- 增加 `/chain [full|intent|order]` 命令，并保留 `/intent` 作为兼容别名。
- `intent` 链路只调用现有意图图。
- `order` 链路调用订单处理子图，并携带历史对话、OrderContext 和参考时间。
- `full` 链路先执行意图图；识别为 `order` 时继续执行订单处理子图。
- 为不同链路提供对应的结构化 CLI 输出；full 链路必须明确展示是否进入订单处理子图、rewrite 是否完成、extract 是否执行或被澄清跳过，以及最终实体数量。
- 明确 full 链路的终点是订单实体提取完成或澄清返回，不是停留在 rewrite 文本输出。
- 保持识别和解析边界：不接入 normalization、reducer、持久化或真实订单业务。

## Capabilities

### New Capabilities

- `cli-chain-entrypoints`: 提供 CLI 的完整、意图和下单三条可切换运行链路。

### Modified Capabilities

- `intent-cli`: 修改 CLI 的链路选择、会话状态和输出行为。

## Impact

影响 `src/inorder_llm/cli/`、CLI 命令入口、主意图图与订单处理子图的组装适配，以及相关测试和 README。复用现有 LangGraph 图与领域模型，不新增外部依赖；旧的 `/intent` 命令保留兼容含义但推荐使用 `/chain intent`。
