## MODIFIED Requirements

### Requirement: Route clarification before extraction

订单处理子图 SHALL 不再设置 rewrite 澄清分支。rewrite 完成后 SHALL 始终进入实体提取，再进入订单上下文更新；LLM 返回非法 JSON 或字段类型错误时仍应抛出结构化错误。

#### Scenario: Rewrite always routes to extraction

- **WHEN** rewrite 返回可解析的重写结果，包括存在不明确指代的结果
- **THEN** 子图 SHALL 调用实体提取器，不得跳过 extract 或进入 clarification 节点

#### Scenario: Invalid rewrite output remains an error

- **WHEN** LLM 返回缺少必填文本字段或字段类型错误的 rewrite JSON
- **THEN** 系统 SHALL 返回结构化解析错误，不得将接口错误当作业务澄清处理
