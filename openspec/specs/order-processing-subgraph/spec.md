# order-processing-subgraph Specification

## Purpose

为订单输入提供一个独立、可测试且仅负责语义解析的 LangGraph 子图，将上下文重写、实体提取和订单草稿更新串联起来，为后续归一化提供稳定输入。

## Requirements

### Requirement: Provide an order processing subgraph

系统 SHALL 提供独立、可测试且仅负责语义解析的订单处理子图，接收本轮用户消息、参考时间、`HistoryConversation` 和 `OrderContext`，依次执行 Rewrite、Extract、实体归一化、上下文 action 合并、货物画像（若启用）、车型处理（若启用）和订单完整性检查，返回重写结果、实体列表、更新后的订单上下文、车型解析及候选等级、结构化订单摘要以及面向用户的自然语言回复。Extract 返回的实体 SHALL 在任何 action 应用前经过一次统一归一化；实体归一化 SHALL 调度现有的时间、手机号、支付/发票/跟车/服务枚举、车型及车型规格规则，保留原始表达、action 和车型匹配状态，并将同一份结果提供给上下文更新与车型处理。上下文 action 合并阶段 SHALL 只应用已归一化实体，不得在其中重复归一化或车型别名/模糊匹配。严格归一化校验失败 SHALL 使本轮处理失败且不产生可返回的部分更新上下文；未匹配的车型表达 SHALL 保留原文供后续车型处理。车型解析结果可以包含 0 至 3 个标记为 `lower_bound_fit` 或 `upper_bound_only` 的候选车型；只有 `lower_bound_fit` 估算主候选可以写入订单上下文，`upper_bound_only` 候选不得作为已选车型写入。用户明确指定的车型 SHALL 保持不变。该子图不得执行真实下单或外部订单副作用。

#### Scenario: Subgraph accepts order parsing state

- **WHEN** 调用方提供有效的用户消息、参考时间、历史对话和订单上下文
- **THEN** 子图能够完成订单语义解析并返回结构化结果

#### Scenario: Subgraph returns updated context

- **WHEN** 子图提取出可应用到订单草稿的实体
- **THEN** 子图返回基于输入订单上下文和本轮实体计算出的新 `OrderContext`

#### Scenario: Subgraph returns vehicle resolution
- **WHEN** 订单解析完成且货物画像或用户车型信息可用于车型决策
- **THEN** 子图返回最终车型、特殊规格、来源和原因

#### Scenario: Subgraph returns ranked vehicle candidates
- **WHEN** 订单解析完成且用户车型不可用或缺失
- **THEN** 子图返回确定性计算得到的 0 至 3 个候选、各自的适配等级和排序原因

#### Scenario: Keep lower-bound candidates ahead of upper-bound-only candidates
- **WHEN** 下界通过和仅上界通过的候选同时存在
- **THEN** 子图返回的候选列表 SHALL 将所有 `lower_bound_fit` 排在 `upper_bound_only` 之前

#### Scenario: Do not commit an upper-bound-only candidate
- **WHEN** 估算结果只有 `upper_bound_only` 候选，没有 `lower_bound_fit` 主候选
- **THEN** 子图返回这些候选，但不得将其中任何车型写入 `OrderContext.vehicle_type` 作为已选估算车型

#### Scenario: Keep an explicitly selected vehicle
- **WHEN** 用户明确指定的车型已匹配
- **THEN** 子图保留用户车型，不因其他估算候选而自动替换

#### Scenario: Process an order through the final summary node
- **WHEN** 订单上下文完成车型处理
- **THEN** 子图执行订单完整性检查作为最后一个节点，并在结果中返回订单状态、事实摘要和缺失字段提示

#### Scenario: Return an incomplete order without failure
- **WHEN** 订单缺少送达时间或其他最小字段
- **THEN** 子图正常完成并返回 `incomplete` 摘要，不将业务字段缺失当作 LangGraph 或 LLM 异常

#### Scenario: Subgraph does not mutate input context

- **WHEN** 子图完成一次解析并返回更新后的订单上下文
- **THEN** 输入的历史对话和原始 `OrderContext` 保持不变

#### Scenario: Normalize extracted entities before applying actions

- **WHEN** Extract 返回订单实体
- **THEN** 子图先统一归一化实体，再应用 action；上下文更新、货物画像和车型处理按该顺序读取本轮最新状态

#### Scenario: Reject strict normalization errors before returning an order result

- **WHEN** 本轮时间、手机号或枚举实体未通过其现有严格归一化校验
- **THEN** 子图调用失败，不返回任何部分更新的 `OrderContext`

#### Scenario: Preserve unmatched vehicle expressions for vehicle processing

- **WHEN** 本轮车型表达无法唯一匹配到标准车型或规格
- **THEN** 子图保留原始表达和 action，车型处理按现有规则判断，上下文 action 合并阶段不把该表达误写为标准车型值

### Requirement: Maintain one working order context during graph processing

订单处理 SHALL 将调用方提供的 `OrderContext` 作为本轮订单快照的起点，并在一次图调用中维护唯一的更新中快照。本轮提取实体 SHALL 表示本轮变更指令，不得作为第二份累计订单状态。系统 SHALL 在应用任何实体 action 前，对 Extract 返回的实体执行一次统一归一化；该阶段 SHALL 对时间、手机号、支付/发票/跟车/服务枚举、车型及车型规格应用各自现有的归一化规则，其他无需转换的实体保持原值。归一化结果 SHALL 保留原始表达和 action，并由上下文更新和车型处理共用。严格校验失败 SHALL 使本轮处理失败且不得返回部分更新上下文；未匹配的车型表达 SHALL 保留原文供后续车型处理。归一化后，系统 SHALL 在货物画像、车型处理和完整性检查之前将实体 action 应用到工作上下文；这些后续阶段 SHALL 读取更新后的上下文。

#### Scenario: Apply cargo actions before derived processing

- **WHEN** 输入上下文已有货物且本轮实体增加、替换或删除货物
- **THEN** 后续货物画像和车型处理使用应用本轮 action 后的货物集合，不读取旧快照或自行再次合并实体

#### Scenario: Normalize supported entity values once

- **WHEN** Extract 返回包含时间、手机号、枚举或车型信息的本轮实体
- **THEN** 系统在应用 action 前按对应规则归一化一次，并由上下文更新和后续车型处理共用结果，同时保留原始表达和 action

#### Scenario: Reject strict normalization errors before applying actions

- **WHEN** 本轮时间、手机号或枚举实体未通过其现有严格校验
- **THEN** 订单处理失败，且本轮任何实体 action 都未写入可返回的更新上下文

#### Scenario: Preserve unmatched vehicle expressions

- **WHEN** 本轮车型表达无法唯一匹配到标准车型或规格
- **THEN** 系统保留原始表达和本轮 action，供后续车型处理按现有规则判断，不将其误写为标准车型值

#### Scenario: Keep the input context immutable

- **WHEN** 图成功完成订单处理
- **THEN** 图返回本轮更新后的上下文，调用方传入的原始 `OrderContext` 保持不变

#### Scenario: Do not return partial context after a downstream failure

- **WHEN** 上下文已在图内更新，但后续货物画像、车型处理或完整性检查失败
- **THEN** 图调用失败且不返回可被调用方当作成功订单结果的部分上下文

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

订单处理子图 SHALL 只负责 rewrite、grounded 实体提取、订单上下文更新、货物画像和确定性车型解析/估算，以及基于当前订单上下文的完整性检查和摘要；不得查询历史订单、读取外部历史订单数据、执行订单创建或确认，不得写入数据库。用户车型匹配成功时不得因货物画像而替换车型。对于提取结果中的业务 attributes，子图 SHALL 原样应用 LLM 已作出的 action 和字段决策，不得自行补全或重判。

#### Scenario: Parsing applies mapped grounded entities in memory only
- **WHEN** 子图提取出带 action 的当前订单实体
- **THEN** 子图将实体的 LLM 决策 attributes 原样应用到当前 `OrderContext` 并返回新上下文，不触发外部业务副作用

#### Scenario: Structured failures do not update context
- **WHEN** rewrite 或 extract 因结构化输出错误导致子图失败
- **THEN** 子图不返回部分更新后的上下文

#### Scenario: Vehicle resolution has no external side effect
- **WHEN** 子图执行车型解析或估算
- **THEN** 结果只更新内存中的订单状态和派生决策，不触发外部业务副作用

#### Scenario: Completeness check has no external side effect
- **WHEN** 子图执行当前订单完整性检查和摘要生成
- **THEN** 系统只读取当前订单上下文并返回摘要，不查询历史订单、不创建订单、不写入数据库且不调用外部服务

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
- **THEN** 父图可以取得 rewrite、entities、OrderContext、车型结果和订单摘要并汇总返回
