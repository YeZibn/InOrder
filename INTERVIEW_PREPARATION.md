# InOrder AI 下单工作流面试准备

## 1. 项目定位

InOrder 是一个面向物流拉货场景的 AI 订单语义解析原型。系统接收用户自然语言、历史对话和当前订单上下文，将非结构化表达转换为可持久化的结构化 `OrderContext`，并通过货物画像和确定性车型推理为后续下单业务提供约束输入。

当前 Python 服务主要负责一次请求内的语义处理，不执行真实订单创建、历史订单查询或支付等业务动作。跨请求的 session、历史对话和订单持久化可以由外部 Java 服务负责。

## 2. 总体架构

```text
客户端 / Java 服务
        │
        │ POST /api/v2/chat
        ▼
Python InOrder API
        │
        ▼
MainGraph（父图）
        │
        ├── IntentGraph（意图子图）
        │       ├── main_intent
        │       ├── sub_intent
        │       ├── build_plan
        │       ├── validate_plan
        │       └── finalize
        │
        └── OrderProcessingGraph（订单处理子图）
                ├── rewrite
                ├── extract
                ├── update_context
                ├── cargo_profile（可选）
                ├── vehicle_resolution（可选）
                └── finalize
```

顶层 `MainGraph` 根据主意图进行条件路由：

- `order`：进入订单处理子图；
- `qa`：进入问答终止分支，目前只返回未实现提示，不执行订单解析。

CLI 提供三种调试入口：

- `full`：运行父图，完整执行意图识别和订单处理；
- `intent`：只运行意图识别子图；
- `order`：只运行订单处理子图。

图层通过 `BaseNode` 和 `BaseGraph` 统一调用边界与编译流程，业务节点仍使用官方 LangGraph `StateGraph` 实现，保证节点职责清晰、状态显式、路由可测试。

## 3. 订单信息创建链路

### 3.1 输入状态

订单处理子图的状态 `OrderGraphState` 主要包含：

```text
message          用户本轮输入
history          HistoryConversation
order_context    当前订单草稿
reference_time   相对时间解析基准
deadline_at      本次工作流截止时间
rewrite_result   重写结果
entities         结构化实体列表
```

其中 `history` 和 `order_context` 是本轮处理的输入快照，节点不直接修改传入对象，避免隐式状态污染。

### 3.2 Rewrite：上下文感知的增量语义重写

`RewriteNode` 将以下内容组合成 LLM 输入：

1. 当前订单上下文；
2. 最近对话历史；
3. 用户本轮消息。

Rewrite 的职责不是直接修改订单，而是把省略、指代和增量表达改写为可抽取的本轮语义，同时保留动作含义：

- `add`：再加、增加、补充；
- `set`：设置、首次声明；
- `remove`：删除、不要、去掉；
- `replace`：改成、替换、换成。

例如已有一吨苹果，本轮输入“再加一吨香蕉”，Rewrite 只输出本轮新增内容的 `extraction_text`，避免把历史字段再次提取成重复更新。

输出采用严格 JSON：

```json
{
  "rewritten_text": "本轮新增一吨香蕉",
  "extraction_text": "再加一吨香蕉"
}
```

### 3.3 Extract：LangExtract grounded entity extraction

默认提取后端为 `langextract`。Prompt 和 schema-covering examples 定义在 `extract/resolver.py`，LangExtract 输出的 grounded extraction 会保留：

- 原文片段 `extraction_text`；
- 实体类别 `extraction_class`；
- LLM 生成的业务属性；
- 字符区间和对齐状态等元数据。

随后由 `LangExtractEntityExtractor` 映射为系统内部统一的 `Entity`：

```python
Entity(
    type="cargo",
    action="add",
    extraction_text="一吨苹果",
    attributes={"name": "苹果", "weight": "1吨"},
)
```

当前支持的主要实体包括：

```text
cargo、location、person、phone、time
vehicle_type、vehicle_specs
follow_car_number、oneself_follow_flag
invoice_type、payment_type、service_type
remark、order_id
```

关键设计是：`action`、地址角色、车型原文等业务语义由模型输出，adapter 只负责结构校验和映射，不使用关键词规则替模型做业务决策。

### 3.4 确定性归一化

LLM 抽取后进入 `normalization` 层，负责可复现的格式归一化：

- 时间：校验 `start/end/context`，添加 `Asia/Shanghai` 时区，并分类为 `fixed` 或 `range`；
- 手机号：清理国际区号和格式分隔符，校验大陆 11 位手机号；
- 枚举：将支付方式、发票类型、服务类型等别名转换为 canonical value；
- 车型：先精确关键词匹配，精确未命中时再使用 RapidFuzz + n-gram Ensemble，并通过阈值、候选差距、数字冲突和语义排除规则控制误匹配。

归一化函数均返回新实体，不修改原实体，便于测试和审计。

### 3.5 OrderContextReducer：纯函数式上下文合并

`OrderContextReducer` 将实体动作应用到复制后的 `OrderContext`：

- 单值字段：`set/replace` 覆盖，`remove` 清空；
- 货物字段：按货物名称定位，支持新增、替换、移除和原始重量/数量/体积/尺寸列表累加；
- 地址、联系人、手机号、时间等字段按实体角色写入对应槽位；
- 未匹配的车型不写入 canonical 车型字段；
- `history` 上下文的时间不会覆盖当前订单配送时间。

`OrderContext` 同时保存原始订单字段和派生字段 `cargo_profiles`、`cargo_profile_summary`。派生画像与原始 `cargo` 分离，保证用户原始表达不会因为估算而丢失。

## 4. 货物画像与车型推理

### 4.1 货物画像

当原始货物发生变化时，`CargoProfileNode` 基于完整货物列表重新生成画像，而不是增量拼接旧画像，避免重复累计。

画像字段包括：

```text
name
weight_kg
volume_m3
dimensions_cm: length / width / height
stackability: full / partial / none / unknown
fragility: low / medium / high / unknown
temperature: ambient / cool / refrigerated / frozen / unknown
reason
```

画像由 LLM 根据货物类型、重量、数量、包装、密度和装载经验进行强制估算。例如只有“一吨苹果”时，也会尝试通过常见单果重量、包装方式和堆积密度推断总体积与整体尺寸；只有完全没有运输规模信息时才允许返回 `null`。

货物画像只描述运输约束，不直接选择车型。

### 4.2 车型主数据

车型数据集中存储于：

```text
src/inorder_llm/catalog/data/vehicles.json
```

`catalog/vehicles.py` 提供统一读取接口，维护：

- 基础车型和标准车长；
- 车型别名与 canonical code；
- 长、宽、高范围；
- 体积范围；
- 载重范围；
- 冷链、厢式、高栏、平板、危险品、高顶、尾板等特殊规格。

车型匹配和车型能力数据共用该主数据源，避免 prompt、代码和测试分别维护不同车型表。

### 4.3 确定性车型估算

`VehicleResolutionResolver` 不调用 LLM 选择车型，处理逻辑为：

1. 用户车型表达能够唯一匹配时，直接采用用户指定车型；
2. 未提供车型或表达无法唯一匹配时，读取货物画像和车型主数据；
3. 先按总重量和总体积进行快速过滤；
4. 将每种货物画像视为一个独立长方体；
5. 对长方体尝试六种旋转方向和可用极点；
6. 检查是否越界以及是否与已放置货物重叠；
7. 按剩余体积、剩余载重等指标排序，最多返回三个候选车型。

该方案将概率性语义理解和确定性能力校验分离：LLM 负责推断货物约束，规则算法负责车辆容量与空间适配。

## 5. LLM 基础设施

### 5.1 统一客户端

`LLMClient` 对上层屏蔽 OpenAI SDK 的具体响应对象，统一返回 `LLMResponse`，包含文本内容、模型标识、token 使用量和安全元数据。

通过环境变量支持：

```text
LLM_API_MODE=chat_completions | responses
LLM_REASONING_EFFORT=low | medium | high
LLM_STREAMING=true | false
LLM_TIMEOUT
LLM_MAX_RETRIES
LLM_BACKOFF_SECONDS
LLM_BACKOFF_MAX_SECONDS
WORKFLOW_TIMEOUT_SECONDS
```

`OpenAITransport` 根据 API 模式构造不同请求：

- Chat Completions 使用 `messages` 和 `reasoning_effort`；
- Responses 使用 `input` 和 `reasoning: {effort: ...}`。

### 5.2 分层重试策略

系统区分三类失败处理：

1. **LLM 传输重试**：只对网络失败、超时、429 和 5xx 等瞬时错误进行有限次数重试，并使用指数退避和上限；
2. **结构化输出修复**：请求成功但 JSON 为空、非法或 schema 不符合时，resolver 最多追加一次格式修复请求；
3. **节点级重试**：默认不自动重放节点，只有显式配置的临时依赖节点才允许有限重试。

流式调用在首个文本增量到达前发生瞬时错误时可以重试；已经向调用方交付增量后发生错误则不重试，避免产生重复输出。

### 5.3 请求级超时

每次 API 请求生成一个 `deadline_at`。`BaseNode` 在节点启动前检查 deadline，工作流超过预算后：

- 不再启动后续节点；
- 通过 SSE 发送 `WORKFLOW_TIMEOUT`；
- 标记 `retryable=false`；
- 不发送 `DONE`。

Python 侧不根据 `session_id` 读取或保存跨请求状态，也不自动重放完整工作流；业务幂等和跨请求重试由外部调用方负责。

## 6. SSE 工作流接口

接口：

```text
POST /api/v2/chat
Content-Type: application/json
Accept: text/event-stream
```

请求字段：

```json
{
  "session_id": "demo",
  "message": "我要运一吨苹果从温州到上海",
  "history": {"turns": []},
  "order_context": {},
  "reference_time": "2026-08-26 10:00"
}
```

事件统一编码为：

```text
data: {"type":"THINKING_STEP","payload":{...}}\n\n
```

公开事件包括：

- `THINKING_START`：开始处理；
- `THINKING_STEP`：识别用户意图、处理订单、生成货物画像、处理车型；
- `THINKING_DONE`：处理完成；
- `CREATE_ORDER_CONTEXT`：推送可持久化订单上下文快照；
- `DONE`：正常终止；
- `ERROR`：归一化错误。

内部的 `rewrite`、`extract`、`update_context` 不作为独立公开阶段，而统一归入“处理订单”，降低前端对内部节点名称的耦合。

SSE 不暴露 prompt、原始模型响应、堆栈或隐藏推理，只输出安全的阶段信息、结构化结果和稳定错误码。

## 7. 测试与可测试性

项目通过 Protocol 和依赖注入隔离外部模型：

- `RewriteModel`；
- `EntityExtractorModel`；
- `CargoProfileModel`；
- `VehicleResolutionModel`；
- 可替换的 LLM transport。

因此单元测试可以使用 fake model 验证节点编排、状态传递、错误传播和重试行为，无需访问真实网关。

测试覆盖重点包括：

- 主图对 `order/qa` 的条件路由；
- Rewrite → Extract → ContextReducer 的顺序和上下文传递；
- 四种实体动作的合并语义；
- 时间、手机号、枚举和车型归一化；
- 货物画像的字段校验、强制估算和原子替换；
- 极点装载的旋转、越界、重叠和最多三个候选；
- LLM 传输重试、错误分类、退避上限和结构化修复；
- SSE 事件顺序、断开连接、错误 payload 和超时行为。

此前在 conda `agent` 环境中完成过完整测试验证：`235 passed, 2 skipped`；跳过项为显式 opt-in 的真实 LLM/LangExtract 网关测试。

## 8. 关键设计取舍

### 为什么使用父图/子图

父图负责全局路由，子图负责领域流程，能够让意图识别和订单处理独立测试、独立调试，也便于以后增加问答子图、历史订单子图和真实订单业务子图。

### 为什么 Rewrite 和 Extract 分离

Rewrite 处理上下文理解和本轮增量语义，Extract 处理 grounded entity extraction。分离后可以避免把历史订单字段误当成本轮修改，也能让抽取 prompt 保持稳定、可测试。

### 为什么车型选择不用 LLM

车型表、载重和车厢尺寸属于固定约束。LLM 适合推断货物的缺失属性，但不适合直接承担确定性容量判断，因此采用“LLM 货物画像 + 规则/几何算法选车”的混合方案。

### 为什么上下文 reducer 要求纯函数

纯函数式 reducer 不修改输入对象，每次返回新上下文，可以避免多轮会话中的隐式副作用，也便于重放、单元测试和失败回滚。

## 9. 当前边界与后续方向

当前已经完成的是“订单语义解析与车型预估原型”，尚未形成真实下单闭环：

- 未接入 Java 订单持久化服务；
- CLI 的 session、历史和订单上下文仍为进程内内存状态；
- 未执行历史订单查询、草稿修改、订单创建和确认下单；
- 当前车型数据来自本地 `vehicles.json`，不是 RPC 动态车型服务；
- API 的 `reference_time` 适合由调用方显式传入，生产环境应在入口统一生成默认值；
- 货物画像是估算结果，后续可增加置信度、人工确认或更专业的装箱算法。

后续可演进为：

1. Python 与 Java 服务之间的稳定请求/响应契约；
2. Java 侧 session、历史、OrderContext 持久化和幂等；
3. 真实订单业务子图；
4. 车型服务 RPC 和区域化车辆库存；
5. 更完整的三维装箱算法与离线评测体系。

## 10. 面试中的一句话总结

这是一个基于 Python 和 LangGraph 的物流订单语义解析系统：通过父子图编排意图识别和订单处理，利用 Rewrite + LangExtract 将多轮自然语言转换为带动作的结构化实体，再由纯函数 reducer 更新 `OrderContext`，结合 LLM 货物画像和确定性极点装载算法完成车型候选筛选，并通过统一 LLM 基础设施和 SSE 暴露稳定、可观测的工作流结果。
