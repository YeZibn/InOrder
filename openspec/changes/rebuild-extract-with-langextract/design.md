## Context

当前 `EntityExtractor` 通过 OpenAI-compatible LLM 请求严格 JSON，并将顶层 `type/action` 解析为旧 `Entity`。订单图只依赖 `EntityExtractorModel.extract()`，因此可以在 extract 包内部替换后端而不改 LangGraph 拓扑。LangExtract 已作为可注入后端接入；本次修订收紧 adapter 职责，消除其中的本地语义推断。

## Goals / Non-Goals

**Goals:**

- 以 LangExtract 的 grounded extraction 结果作为提取层原始输出。
- 保留原文片段和可选位置元数据。
- 将 action 放入 attributes，并无推断地复制到 reducer 可消费的兼容实体。
- 将 LLM 的空提取原样返回，保持其作为一次有效模型决策的语义。
- 保留现有 `EntityExtractorModel` 接口和测试替身能力。

**Non-Goals:**

- 不改变 rewrite、OrderContextReducer 或 LangGraph 节点拓扑。
- 不在本 change 中实现复杂地址、货物体积或车型推断。
- 不同时运行两个生产后端；JSON 后端仅作为迁移/回滚参考。
- 不新增外部订单服务或数据库。
- 不在 adapter 中用关键词、正则、实体顺序或默认值推断任何订单业务字段。

## Decisions

1. **分层模型。**
   新增 grounded extraction 数据模型，字段为 `extraction_class`、`extraction_text`、`attributes` 和 `metadata`；对 reducer 的兼容实体由 mapper 生成，避免让 LangExtract API 泄漏到图层。

2. **action 放在 attributes，且由 LLM 决策。**
   action 是实体语义属性，与 cargo 的 name/weight、location 的 role 同层。adapter 仅在 action 符合接口枚举时将 `attributes["action"]` 复制到兼容对象；不得根据文本补默认值或覆盖模型值。

3. **原文定位优先。**
   LangExtract examples 要求每条结果对应输入中的原文片段；位置/对齐信息作为 metadata 保存。adapter 可校验结果是否满足数据接口，但不得基于原文补造业务字段。

4. **mapper 无业务补全。**
   LangExtract/LLM 负责分类、原文片段、地址 `role`、action、车型/规格 code 和其他业务 attributes。mapper 只进行字段复制、兼容对象构造及数据契约校验；后续 normalization 仍由现有流程负责。

5. **空提取由 LLM 决定。**
   后端返回空列表时直接返回空列表，不根据输入文本判断其是否应为订单，也不转换为错误或澄清。CLI 或调用方可以将空结果作为观测信息展示，但不得改变该结果的业务语义。

6. **后端配置与可测试性。**
   提供 LangExtract extractor 的依赖注入和模型配置；通过 fake backend 测试，不让普通单元测试调用网络。生产默认使用 LangExtract，失败时不隐式回退到旧 JSON，避免结果语义不一致。

## Risks / Trade-offs

- [Risk] LangExtract API/版本变化 → 将具体调用封装在单一 adapter，并锁定兼容版本。
- [Risk] LLM 可能遗漏实体或返回空列表 → 保留 grounded 原文、prompt examples 和真实探针，后续以评测集改进模型侧行为；adapter 不做本地补偿。
- [Risk] LLM 输出缺少 reducer 所需字段 → 将其作为明确的输出契约错误暴露，不使用默认值掩盖。
- [Risk] 新模型与旧测试契约不同 → 保留兼容转换层并逐步迁移测试，而不是一次改动 reducer。
