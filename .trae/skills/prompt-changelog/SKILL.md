---
name: "prompt-changelog"
description: "修改 LLM prompt 时自动向 PROMPT_CHANGELOG.md 追加变更记录（摘要/原因/关联/评测结果）。当改动 prompt 常量或用户要求记录 prompt 变更时调用。"
---

# Prompt Changelog

当 `inorder_llm` 中的 LLM prompt 发生变更时，向 `src/inorder_llm/intent/PROMPT_CHANGELOG.md` 追加一条变更记录，确保每次 prompt 修改都有可追溯的「变更 → 原因 → 评测」闭环。

## 何时触发

满足以下任一条件即应调用本 skill：

- 修改了 `src/inorder_llm/intent/resolver.py` 中的 `MAIN_INTENT_SYSTEM_PROMPT` 或 `SUB_INTENT_SYSTEM_PROMPT`（或后续新增的 `*_SYSTEM_PROMPT` / prompt 常量）。
- 用户显式要求记录 prompt 变更。
- 在一个 OpenSpec change 中实施了 prompt 改动。

## 记录位置

`src/inorder_llm/intent/PROMPT_CHANGELOG.md` 的「## 记录」节下，追加一条记录（与既有记录的日期排序方式保持一致）。

## 流程

1. **识别变更**：对比修改前后，确认哪些 prompt 常量被改、改了什么（定义 / 规则 / 边界示例 / JSON schema / 消息角色 等）。
2. **追加记录**：在 `PROMPT_CHANGELOG.md` 追加一条，字段如下：
   - 日期 (YYYY-MM-DD)
   - **Prompt**：受影响的常量名
   - **变更摘要**：新旧差异要点
   - **原因**：动机 / 触发场景
   - **关联**：OpenSpec change 名 / commit / PR
   - **评测结果**：见第 3 步
3. **填写评测结果**：尽量给出可复现依据，至少包含：
   - 单测命令与结果（如 `conda run -n agent python -m pytest -q` → N passed）
   - 若新增 / 调整了 prompt 相关断言，注明所在测试文件
   - 典型 case 表现（若人工抽检）
   - 若有真实 LLM 评测集，记录得分；若无，注明「待评测集补充」
4. **不要删除或改写既有记录**，只追加。

## 注意

- 评测结果字段禁止只写「通过」，必须附命令或用例依据。
- 若一次改动涉及多个 prompt，可合并为一条记录，在「Prompt」字段列出全部受影响常量。
- 若改动是纯格式 / 空格调整且不影响行为，仍建议追加一条并在「原因」注明「非功能性」。
