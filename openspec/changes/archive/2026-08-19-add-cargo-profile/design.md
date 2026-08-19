## Context

当前 `OrderContext.cargo` 保存由 extract/reducer 产生的原始字符串列表，画像需要读取这份完整快照并生成独立派生结果。现有 LLM 客户端、结构化错误约定和 LangGraph 订单子图可作为接入边界；本设计不改变原始 cargo reducer，也不提前引入车型目录校验。

## Goals / Non-Goals

**Goals:**

- 建立 backend-neutral 的货物画像模型和 LLM resolver 接口。
- 使用严格 JSON prompt 生成每种货物画像及汇总重量/总体积。
- 对输出做契约校验，保留 `basis`、`confidence`、`assumptions`、`warnings`。
- 在订单上下文中整体替换派生画像，保证与当前原始货物一致。

**Non-Goals:**

- 不进行车型推荐、车型枚举归一或车辆规格匹配。
- 不实现 3D 装箱、极点法、碰撞检测或多车优化。
- 不把画像估算值写回原始 cargo，也不在本地用关键词推断货物属性。

## Decisions

1. **原始事实与派生画像分离**：保留现有 `cargo` 结构作为唯一原始输入；新增 `cargo_profiles` 与 `cargo_profile_summary` 字段。这样可以重新生成画像并支持未来更换估算策略。

2. **单次 LLM 调用生成完整快照**：resolver 输入整个货物列表，输出所有画像和汇总，避免逐条调用造成总量不一致。画像发生变化时重新生成全量结果并整体替换。

3. **字段采用带来源的对象**：数量、重量、尺寸、体积和运输属性都携带来源/置信度；未知值使用 `null` 或 `unknown`，不由本地逻辑填充。

4. **总体积定义为装车占用体积**：这是后续车型空间校验需要的指标。明确体积、尺寸推导和 LLM 估算都必须标注 basis，无法可靠计算时汇总状态为 `partial`/`unknown`。

5. **LLM 负责语义推断，兼容层只校验契约**：本地代码只验证 JSON 类型、枚举、数值范围和必需字段，不根据货名或关键词补全易碎、堆叠、温度等语义。

6. **可注入 backend**：定义画像 resolver/backend 协议，默认使用现有 OpenAI-compatible LLM 客户端，测试可以注入固定响应，不依赖真实网络。

## Risks / Trade-offs

- [LLM 估算不准确] → 保存 basis、confidence、assumptions 和 warnings；低置信度结果不能伪装成明确事实。
- [原始重量表达存在增量/重复歧义] → resolver 不擅自相加，返回 warning 或 unknown。
- [画像字段扩展导致上下文结构变化] → 所有新增字段保持 JSON-compatible，并允许为空；旧会话缺少画像字段时按未生成处理。
- [全量调用成本增加] → 只在 cargo 发生变化后调用，后续可加入基于 cargo 快照的缓存而不改变契约。

## Migration Plan

1. 增加可选画像字段和模型，旧 OrderContext 序列化保持兼容。
2. 增加 resolver/backend 与结构化校验，先通过单元测试验证。
3. 在订单处理链路中以显式节点或调用点接入，失败时保留原始 cargo，画像不更新。
4. 如需回滚，停止画像节点调用即可；原始货物 reducer 和既有订单解析不受影响。
