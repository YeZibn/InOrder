## 1. 主意图 prompt 重写

- [x] 1.1 将 `MAIN_INTENT_SYSTEM_PROMPT` 的 `order` 定义从「要求系统执行…操作」改为「期望输出是行动/结果的业务目标意愿」，判据为期望输出类型而非命令动词
- [x] 1.2 在 `MAIN_INTENT_SYSTEM_PROMPT` 加入领域映射：运货/发货/配送/托运/下单 = `order` 业务目标词
- [x] 1.3 在 `MAIN_INTENT_SYSTEM_PROMPT` 加入咨询信号闸门词（了解/咨询/怎么/多少钱/能不能/一般），存在时即使提及业务目标也归 `qa`
- [x] 1.4 更新 `MAIN_INTENT_SYSTEM_PROMPT` 边界示例：新增「我想从上海运货到温州」→ `order`、「运货到温州多少钱」→ `qa`、「上海到温州能运吗」→ `qa`

## 2. 子意图 prompt 领域映射

- [x] 2.1 在 `SUB_INTENT_SYSTEM_PROMPT` 加入「运货/发货/配送 需求映射为 `create_order`」领域映射说明

## 3. 测试更新

- [x] 3.1 更新 `tests/test_intent_resolver.py`：断言 prompt 含业务目标词、咨询信号闸门词、期望输出判据关键词
- [x] 3.2 更新 `tests/test_intent_graph.py`：补充「我想从上海运货到温州」→ 路由 `order`、「上海到温州能运吗」→ 路由 `qa` 的用例（基于 mock 意图识别器）

## 4. 变更记录与验证

- [x] 4.1 按 `prompt-changelog` skill 向 `src/inorder_llm/intent/PROMPT_CHANGELOG.md` 追加一条变更记录（含评测结果）
- [x] 4.2 运行 `conda run -n agent python -m pytest -q` 确认全部通过
