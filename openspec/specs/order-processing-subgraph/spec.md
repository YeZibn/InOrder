# order-processing-subgraph Specification

## Purpose

为订单输入提供一个独立、可测试且仅负责语义解析的 LangGraph 子图，将上下文重写、实体提取和订单草稿更新串联起来，为后续归一化提供稳定输入。

## Requirements

### Requirement: Provide an order processing subgraph

系统 SHALL 提供独立的订单处理子图，接收本轮用户消息、参考时间、`HistoryConversation` 和 `OrderContext`，并返回重写结果、实体列表、更新后的订单上下文及车型解析结果；车型解析结果可以包含 0 至 3 个候选车型。

#### Scenario: Subgraph accepts order parsing state

- **WHEN** 调用方提供有效的用户消息、参考时间、历史对话和订单上下文
- **THEN** 子图能够完成订单语义解析并返回结构化结果

#### Scenario: Subgraph returns updated context

- **WHEN** 子图提取出可应用到订单草稿的实体
- **THEN** 子图返回基于输入订单上下文和本轮实体计算出的新 `OrderContext`

#### Scenario: Subgraph returns vehicle resolution
- **WHEN** 订单解析完成且货物画像或用户车型信息可用于车型决策
- **THEN** 子图返回最终车型、特殊规格、来源和原因

#### Scenario: Subgraph returns vehicle candidates
- **WHEN** 订单解析完成且用户车型不可用或缺失
- **THEN** 子图返回确定性计算得到的 0 至 3 个车型候选及其来源和原因

#### Scenario: Subgraph does not mutate input context

- **WHEN** 子图完成一次解析并返回更新后的订单上下文
- **THEN** 输入的历史对话和原始 `OrderContext` 保持不变

### Requirement: Rewrite before extraction

系统 SHALL 先使用当前消息、历史对话和订单上下文生成 rewrite 结果，再将 rewrite 结果中的 `extraction_text` 与 reference time 提供给实体提取阶段。实体提取阶段不得再次读取原始消息、历史对话或订单上下文。

#### Scenario: Extract incremental request after rewrite

- **WHEN** 当前订单已有一吨苹果，用户输入“再加一吨苹果”
- **THEN** 子图保留 rewrite 的增量动作语义，并将对应 `extraction_text` 用于提取 `cargo` 的 `add` entity

#### Scenario: Extraction uses rewritten extraction text

- **WHEN** rewrite 成功返回 `extraction_text`
- **THEN** extract 阶段仅使用该文本与 reference time，而不是再次读取原始消息、历史或订单上下文

### Requirement: Always extract after rewrite

系统 SHALL 不设置 rewrite 澄清分支。rewrite 完成后 SHALL 始终进入实体提取，再进入订单上下文更新。

#### Scenario: Ambiguous rewrite still reaches extraction

- **WHEN** rewrite 返回可解析的重写结果，包括存在不明确指代的结果
- **THEN** 子图 SHALL 调用实体提取器，不得跳过 extract 或进入 clarification 节点

### Requirement: Keep parsing-only boundary

订单处理子图 SHALL 只负责 rewrite、grounded 实体提取、订单上下文更新、货物画像和确定性车型解析/估算；不得调用历史订单服务、订单创建或确认工具，不得写入数据库。用户车型匹配成功时不得因货物画像而替换车型。对于提取结果中的业务 attributes，子图 SHALL 原样应用 LLM 已作出的 action 和字段决策，不得自行补全或重判。

#### Scenario: Parsing applies mapped grounded entities in memory only

- **WHEN** 子图提取出带 action 的订单实体
- **THEN** 子图将实体的 LLM 决策 attributes 原样应用到当前 `OrderContext` 并返回新上下文，不触发外部业务副作用

#### Scenario: Clarification does not update context

- **WHEN** rewrite 触发澄清并跳过 extract
- **THEN** 子图返回原始订单上下文作为当前上下文，不应用实体更新

#### Scenario: Structured failures do not update context

- **WHEN** rewrite 或 extract 因结构化输出错误导致子图失败
- **THEN** 子图不返回部分更新后的上下文

#### Scenario: Vehicle resolution has no external side effect
- **WHEN** 子图执行车型解析或估算
- **THEN** 结果只更新内存中的订单状态和派生决策，不触发外部业务副作用

### Requirement: Surface structured failures

系统 SHALL 将 rewrite 或 extract 的结构化输出错误作为子图调用错误暴露，不返回部分成功结果。

#### Scenario: Invalid rewrite output

- **WHEN** rewrite 模型返回非法 JSON 或缺失必需字段
- **THEN** 子图调用失败并暴露结构化错误，不调用 extract

#### Scenario: Invalid extraction output

- **WHEN** rewrite 成功但 extract 模型返回非法结构
- **THEN** 子图调用失败并暴露结构化错误，不产生可被误用的部分结果

#### Scenario: Vehicle estimation has no LLM selection call
- **WHEN** 子图进入车型估算阶段
- **THEN** 车型结果由车型主数据和确定性装载计算生成，不调用车型选择 LLM

### Requirement: Parent graph embeddable order subgraph

订单处理图 SHALL 可独立调用，也 SHALL 能作为 MainGraph 的子图挂载；接收父图传入的消息、参考时间、历史对话和订单上下文，并返回可汇总的订单处理结果。

#### Scenario: Parent graph passes order context
- **WHEN** MainGraph 路由到订单子图
- **THEN** 订单子图接收父图传入的历史对话、订单上下文和参考时间

#### Scenario: Order subgraph output returns to parent
- **WHEN** 订单子图完成解析
- **THEN** 父图可以取得 rewrite、entities、OrderContext 和车型结果并汇总返回
