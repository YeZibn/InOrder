## Context

当前 extract prompt 已定义四类订单枚举，但 LLM 输出可能是中文表达、别名、整数或 service code；`OrderContextReducer` 不应承担自然语言解析。归一化需要位于 extract 与 reducer 之间，并保持独立、纯函数式行为。

## Goals / Non-Goals

**Goals:**

- 为四类枚举建立集中、可测试的映射表。
- 支持中文别名和已归一化值，保证幂等。
- 保留原始表达，并对未知值提供可诊断错误。
- 在不改变当前整数字段契约的前提下，将 service_type 稳定为内部 code。

**Non-Goals:**

- 不处理车型、跟车人数、度量单位、地址或货物属性推断。
- 不接入 LangGraph，不调用外部字典或订单服务。
- 不在本次变更中重新定义“不开票/电子普票”的现有业务编码。

## Decisions

### 独立的枚举归一化模块

新增 normalization 领域模块，由模块接收 `Entity` 并返回归一化实体；reducer 只处理稳定值。相比把映射散落在 prompt 或 reducer 中，集中模块更容易测试、复用和保持幂等。

### 保持现有字段编码

`payment_type`、`invoice_type`、`oneself_follow_flag` 继续使用当前整数值；`service_type` 使用 `express`、`urgent`、`user_bid`、`shared`。这样避免不必要的数据迁移，同时让服务类型不依赖展示中文。

### 未知值显式失败

无法映射的枚举不进行相似猜测。归一化接口应返回结构化错误，包含实体类型、原始值和支持范围；调用方可以决定是否进入澄清流程。

### 原始值与规范值并存

归一化实体保留 `raw` 或等价元数据，同时将规范值写入现有 `value` 属性。该方案兼顾内部计算、用户展示和审计；不把展示字段改造成新的上下文模型。

## Risks / Trade-offs

- [别名覆盖不足] → 先维护有限、明确的别名表；未知表达显式暴露，后续通过测试补充。
- [现有 prompt 与代码映射不一致] → 用共享常量或集中映射作为代码层事实，并增加契约测试。
- [service_type code 变更影响消费者] → 首次引入时仅在归一化输出阶段使用 code，并同步 reducer/测试，避免隐式混用中文值。
