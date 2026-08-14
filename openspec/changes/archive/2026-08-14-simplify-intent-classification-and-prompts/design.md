## Context

当前 `LLMIntentModel` 使用短字符串拼接 prompt，主意图和子意图规则不够明确；图在 `main_intent` 后还包含 ambiguous/clarification 分支。新行为需要同步领域枚举、路由和 prompt 合同。

## Goals / Non-Goals

**Goals:**

- 将主意图固定为 `order`、`qa`。
- 以“明确执行请求优先”为混合消息决策规则。
- 使用稳定、可测试的 system prompt，并将用户消息作为独立 user message 发送。
- 保留 order 下的多子意图和 `depends_on`。

**Non-Goals:**

- 不实现订单业务操作或真实问答。
- 不根据 confidence 增加隐式第三分支。
- 不改变子意图名称和 IntentPlan 字段结构。

## Decisions

### 两分类优先级

`order` 表示需要系统执行，`qa` 表示只需要信息；混合消息只要存在明确执行动作就归为 `order`。相比保留 ambiguous，这能让图继续进入可执行的识别路径，减少无效停顿。

### Prompt 分层

主意图 prompt 负责定义两类边界和严格 JSON schema；子意图 prompt 只在主意图为 order 时执行，负责多步骤识别、参数保守提取和依赖关系表达。用户消息作为独立 user message 传给 LLM，避免把不可信输入拼进 system 指令。

### 澄清范围

删除主意图 ambiguous 澄清；`needs_clarification` 仍由计划构建节点在 order 无子意图时设置，后续可扩展为必要字段缺失提示。

## Risks / Trade-offs

- [部分旧 mock 返回 ambiguous] → 更新测试和校验错误信息，要求迁移到两分类。
- [执行/询问边界仍可能依赖语言表达] → prompt 中加入成对示例和执行优先规则。
- [LLM 输出非 JSON] → 保留现有结构化响应异常处理。

## Migration Plan

1. 更新主规格和领域枚举/校验。
2. 重写 resolver 的两个 prompt 及消息构造。
3. 移除图 ambiguous 节点和路由。
4. 更新测试、CLI 输出和 README 示例。
5. 在 conda `agent` 环境运行全量测试。
