---
name: "prompt-changelog"
description: "修改 LLM prompt 时自动向 PROMPT_CHANGELOG.md 追加变更记录（摘要/原因/关联/评测结果）。当改动 prompt 常量或用户要求记录 prompt 变更时调用。"
---

# Prompt Changelog

当 `inorder_llm` 中的 LLM prompt 发生变更时，向 `src/inorder_llm/PROMPT_CHANGELOG.md` 追加一条变更记录，确保每次 prompt 修改都有可追溯的「变更 → 原因 → 评测」闭环。

## 何时触发

满足以下任一条件即应调用本 skill：

- 修改了 `src/inorder_llm/` 下任意模块中的 `*_SYSTEM_PROMPT` / prompt 常量（如 `intent/resolver.py` 的 `MAIN_INTENT_SYSTEM_PROMPT`、`extract/resolver.py` 的 `EXTRACTION_SYSTEM_PROMPT`，及后续新增的 prompt 常量）。
- 用户显式要求记录 prompt 变更。
- 在一个 OpenSpec change 中实施了 prompt 改动。

## 记录位置与结构

`src/inorder_llm/PROMPT_CHANGELOG.md`（统一 changelog，覆盖所有模块）。结构按 **prompt 常量分层**：

- `###` 标题为 prompt 常量名（括号标注所在文件），如 `### \`MAIN_INTENT_SYSTEM_PROMPT\`（\`intent/resolver.py\`）`
- `####` 标题为变更日期（YYYY-MM-DD），同一 prompt 下按时间正序排列
- 不同 prompt 之间用 `---` 分隔线隔开

若受影响的 prompt 常量已有 `###` 标题，在其下追加新的 `####` 日期条目；若是新 prompt 常量，在「## 记录」节末尾新建 `###` 标题。

## 流程

1. **确定日期**：运行 `date "+%Y-%m-%d %A"` 获取系统真实日期，以此作为记录日期。环境注入的日期可能与系统真实日期不符，**必须以 `date` 命令输出为准**，不要直接信任环境上下文中的日期。
2. **识别变更**：对比修改前后，确认哪些 prompt 常量被改、改了什么（定义 / 规则 / 边界示例 / JSON schema / 消息角色 等）。
3. **定位或创建 prompt 标题**：在「## 记录」节下找到受影响 prompt 常量的 `###` 标题；若不存在则新建。
4. **追加日期条目**：在该 prompt 标题下追加 `####` 日期条目，字段如下：
   - **变更摘要**：新旧差异要点，聚焦本 prompt 的具体变化
   - **原因**：动机 / 触发场景
   - **关联**：OpenSpec change 名 / commit / PR
   - **评测结果**：见第 5 步
5. **填写评测结果**：尽量给出可复现依据，至少包含：
   - 单测命令与结果（如 `conda run -n agent python -m pytest -q` → N passed）
   - 若新增 / 调整了 prompt 相关断言，注明所在测试文件
   - 典型 case 表现（若人工抽检）
   - 若有真实 LLM 评测集，记录得分；若无，注明「待评测集补充」
6. **不要删除或改写既有记录**，只追加。

## 注意

- 评测结果字段禁止只写「通过」，必须附命令或用例依据。
- 若一次改动涉及多个 prompt，**每个 prompt 各自在其 `###` 标题下追加一条 `####` 日期条目**，变更摘要聚焦各自的变化，不要合并为一条。
- 若改动是纯格式 / 空格调整且不影响行为，仍建议追加一条并在「原因」注明「非功能性」。
