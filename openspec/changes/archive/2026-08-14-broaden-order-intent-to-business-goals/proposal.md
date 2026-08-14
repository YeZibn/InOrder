## Why

当前主意图 `order` 的判定锚点偏「显式系统操作命令」（创建/修改/查询订单），导致用户用业务目标语言表达的订单需求（如「我想从上海运货到温州」）被误判为 `qa`，真实订单需求在主意图层就丢失。需要把 `order` 锚点从「执行命令动词」扩到「期望输出（行动 vs 信息）」，让业务目标陈述归 `order`、咨询信号归 `qa`。

## What Changes

- 把 `MAIN_INTENT_SYSTEM_PROMPT` 的 `order` 定义从「要求系统执行…操作」改为「期望输出是行动/结果的业务目标意愿（直接指令或愿望陈述均可）」，判据从动词类型转向用户期望的输出类型。
- 在 prompt 注入领域映射：`MAIN_INTENT_SYSTEM_PROMPT` 增加 运货/发货/配送/托运/下单 = `order` 业务目标词；`SUB_INTENT_SYSTEM_PROMPT` 增加 运货/发货/配送 需求映射为 `create_order`（两层都需跨过语义鸿沟，否则主意图判对但子意图提取失败）。
- 在 prompt 加入咨询信号闸门词：当存在 了解/咨询/怎么/多少钱/能不能/一般 等信息询问信号时，即使提及业务目标也归 `qa`，防止过度归 `order`。
- 确立字面派判定原则：意图分类只认用户字面期望输出，深层需求推测交给对话策略层（本 change 仅确立该判定边界原则，不在代码层实现对话策略）。
- 更新测试：补充 `order` 业务目标 case 与 `qa` 咨询信号 case 的断言。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `intent-planning`: 修改 `Main intent classification` 需求——`order` 锚点扩展到业务目标愿望陈述，补充「业务目标愿望归 order」「业务目标含咨询信号归 qa」两个边界 scenario，并明确判据为期望输出类型而非命令动词。

## Impact

- `src/inorder_llm/intent/resolver.py`：`MAIN_INTENT_SYSTEM_PROMPT` 定义、规则、边界示例重写并加入领域映射与闸门词；`SUB_INTENT_SYSTEM_PROMPT` 加入「运货/发货/配送 → `create_order`」领域映射说明。
- `tests/test_intent_resolver.py`：prompt 内容断言更新（新增业务目标词、咨询信号闸门词断言）。
- `tests/test_intent_graph.py`：补充业务目标 case 路由到 `order`、咨询 case 路由到 `qa` 的用例。
- `src/inorder_llm/intent/PROMPT_CHANGELOG.md`：按 `prompt-changelog` skill 追加一条变更记录。
- 无 API/Protocol 接口变化（`classify_main_intent` 签名不变）；属 prompt 行为契约变更，会影响 LLM 实际分类输出。
