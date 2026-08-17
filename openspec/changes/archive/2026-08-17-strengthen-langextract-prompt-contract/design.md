## Context

当前 LangExtract adapter 在自身模块中定义简短 description 和两个 few-shot examples。LangExtract OpenAI provider 会从 examples 收集 extraction class 与 attributes 生成 strict schema，因此当前运行时只允许 cargo 与 location。订单子图已经先执行 rewrite，但 extract 仍接收 history 并把其拼接到 grounded source 中。

## Goals / Non-Goals

**Goals:**

- 使 `extract/resolver.py` 成为订单提取 prompt、实体契约与 LangExtract examples 的唯一语义定义位置。
- 让 examples 同时覆盖所有支持的 entity class 和 attributes，生成完整 strict schema。
- 确保 extraction text 只能来自 rewrite 的本轮待提取文本。
- 保持 adapter 无语义推断，并保持 JSON backend 作为显式回退选项可用。

**Non-Goals:**

- 不改变 rewrite 的消歧、OrderContextReducer 的合并规则或 normalization 的格式校验职责。
- 不实现新的货物体积推断、地址服务或订单 API。
- 不让 extract 重新读取或重新解释完整 OrderContext。

## Decisions

1. **Prompt 归属 `extract/resolver.py`。**
   在该模块定义 `LANGEXTRACT_ORDER_PROMPT_DESCRIPTION` 与创建 examples 的工厂函数；adapter 仅导入它们并传给 LangExtract。保留原有 JSON prompt，服务于显式 `json` 回退后端。

2. **Examples 是 schema 的来源。**
   每个 entity class 至少有一个 grounded example；该类可返回的每个 attribute 至少在一个 example 中出现。examples 中均包含 action，缺失字段以 LangExtract strict schema 所要求的 null 表达，不由 adapter 补全。选择 examples-generated schema，而非手写 JSON schema，以复用 LangExtract 的解析与对齐格式。

3. **Extract 输入收敛。**
   rewrite 是 history 与 OrderContext 的唯一消费者。ExtractNode 向 extractor 传入 `extraction_text` 和 `reference_time`；adapter 生成的 source 使用显式的“参考时间”和“待提取文本”分段，prompt 禁止从前者生成实体原文。JSON fallback 同步采用该接口，以保持图的 extractor boundary 单一。

4. **LLM 决定语义，代码校验契约。**
   LLM 输出 action、location role、各类 attributes 和 canonical code。adapter 只验证 action、基本字段类型与 grounded 数据可读性，并复制到兼容 Entity。normalization 保留其已有的后置格式校验/规范化职责，不判断 action 或地址 role。

5. **Remark 分离原文和摘要。**
   remark 的 extraction_text 必须是用户原文；简短业务摘要放在 attributes.value。这避免摘要无法对齐原文，同时保持 reducer 可消费的备注值。

## Risks / Trade-offs

- [Risk] 完整 schema 增加 prompt token 与 examples 数量 → 使用覆盖多个实体的组合 examples，并保留每类至少一个独立边界示例。
- [Risk] strict schema 要求可选 fields 显式为 null → 在 prompt 与 examples 中明确空值行为，并为 schema 构造添加回归断言。
- [Risk] 移除 extract history 参数影响 JSON fallback 和测试替身 → 同步更新协议、旧 resolver 和所有 fake extractor；图只维护一种调用形式。
- [Risk] LLM 仍可能漏提实体 → 通过覆盖 14 类的离线 contract tests 与 opt-in live probes 观测，不在 adapter 中加入语义兜底。

## Migration Plan

1. 在 resolver 中加入完整 LangExtract prompt、catalog-derived code 文本与 examples 工厂。
2. 切换 adapter 使用 resolver 定义，并更新 extractor protocol、图节点和 JSON fallback 的参数边界。
3. 更新测试，先验证 schema 覆盖和 source boundary，再运行 live probes 与全量套件。
4. 若新 prompt 在网关上不兼容，设置 `EXTRACTOR_BACKEND=json` 临时回退；不得在一次请求内自动混用后端。
