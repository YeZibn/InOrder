## Context

当前 rewrite 和 extract 已分别实现为可注入 LLM client 的纯模块，主意图图也已使用 LangGraph 编排主意图和子意图识别。本 change 只增加独立订单处理子图，不改造现有主意图图，也不把解析结果写入订单上下文。

## Goals / Non-Goals

**Goals:**

- 用 LangGraph StateGraph 编排 rewrite → 澄清路由 → extract。
- 为子图定义独立状态，显式携带消息、参考时间、历史和订单上下文。
- 通过依赖注入复用已有 rewrite model 和 entity extractor，支持纯 mock 测试。
- 在澄清分支阻止 extract，在成功分支返回结构化实体。

**Non-Goals:**

- 不将子图嵌入现有主意图图。
- 不执行 normalization 或 `OrderContextReducer`。
- 不查询历史订单，不创建、修改或确认订单。
- 不新增外部依赖或持久化机制。

## Decisions

### 独立 `graph/order` 包

订单处理图放在 `src/inorder_llm/graph/order/`，与现有 `graph/intent/` 并列。这样订单解析子图可独立编译、调用和测试，未来再由主图作为 order 分支嵌入。

### 子图状态显式携带领域对象

状态包含 `message`、`reference_time`、`history`、`order_context`、`rewrite_result`、`entities` 以及澄清字段。历史和订单上下文作为 rewrite 的只读输入，不在图节点之间通过隐式全局状态传递。

### 节点依赖注入协议

图构建函数接收 rewrite model 和 extractor。节点只依赖最小调用协议，而不依赖具体 LLM client；测试可以注入记录调用次数的 fake 实现，验证澄清时 extract 未执行。

### 使用 `extraction_text` 作为 extract 输入

extract 节点读取 rewrite 结果的 `extraction_text`，并使用显式的 `reference_time` 和历史参数完成提取。这样 rewrite 负责上下文消解，extract 负责实体结构化，避免重复推理。

### 澄清路由使用条件边

rewrite 节点后通过条件路由选择 `extract` 或 `finalize`。澄清出口将实体结果设为空，并保留完整 `RewriteResult`，不创建额外业务澄清服务。

### finalize 只组装结果

finalize 节点只规范化子图返回字段，不调用 reducer，不改变传入的 `HistoryConversation` 或 `OrderContext`。错误由节点直接抛出，交给 LangGraph 调用方处理。

## Risks / Trade-offs

- [子图尚未接入主意图图] → 先提供独立入口和完整测试，后续单独 change 处理主图嵌入。
- [rewrite 输出为空 extraction_text] → 成功路径由 extractor 负责处理空文本或返回结构化错误；本 change 不自行猜测用户意图。
- [历史参数可能过长] → 复用 rewrite/extract 现有的显式 history 传入机制，保留 history limit 由模型层控制；持久化和摘要另行设计。

## Migration Plan

新增模块和测试不改变现有调用方。未来主意图图接入时，在 `order` 分支调用该子图，并将其结果映射到主图状态；若接入失败，可继续使用当前仅识别意图的主图。
