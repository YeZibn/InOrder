## MODIFIED Requirements

### Requirement: CLI provides selectable chain entrypoints
CLI MUST 保持 full、intent、order 三条链路的选择方式，并可在不改变链路语义的前提下展示 LLM 流式增量内容。

#### Scenario: Select chain
- **WHEN** 用户通过现有命令选择 full、intent 或 order
- **THEN** CLI MUST 执行对应链路

#### Scenario: Stream within selected chain
- **WHEN** 所选链路触发 LLM 调用且流式展示已启用
- **THEN** CLI MUST 实时显示增量，并继续输出原有结构化链路结果
