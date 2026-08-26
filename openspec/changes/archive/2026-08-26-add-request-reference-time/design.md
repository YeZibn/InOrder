## Context

当前 CLI 在 `CliSession` 创建时生成参考时间，长期运行时该值可能跨天过期；HTTP API 在未传入 `reference_time` 时将空字符串写入 state，而 Extract 的时间格式化要求 `YYYY-MM-DD HH:MM`。订单图已经将参考时间作为 state 字段传递给 Extract，但 Rewrite 尚未共享该请求级时间锚点。

## Goals / Non-Goals

**Goals:**

- 在 CLI 消息入口和 HTTP 请求入口统一确定本轮参考时间。
- 支持调用方传入可重放的参考时间；未传入时生成 Asia/Shanghai 当前时间。
- 让一次工作流内的 Rewrite、Extract、后续节点和结构化修复重试复用同一值。
- 防止空字符串、非法格式和跨节点重新取当前时间。

**Non-Goals:**

- 不把参考时间写入 `OrderContext` 业务字段。
- 不改变时间实体的 fixed/range 归一化规则。
- 不实现跨请求时间持久化或 session 恢复。

## Decisions

### 1. 在请求边界生成，而不是在 Extract 内部生成

CLI 每轮消息开始时、HTTP API 校验请求后生成一次时间，并写入 Graph State。Extract 只消费显式值并负责格式化；这样 Rewrite 与 Extract 使用相同时间，且重试不会因系统时钟变化得到不同结果。

备选方案是在 Extract 内部调用 `datetime.now()`，但这会让同一请求的不同节点拥有不同时间，也不利于请求重放，因此不采用。

### 2. 外部值优先，默认值兜底

有效的调用方 `reference_time` 保留原值，便于回放历史请求和测试；缺失或空值时使用 `datetime.now(ZoneInfo("Asia/Shanghai"))` 格式化为 `YYYY-MM-DD HH:MM`。格式校验放在入口，避免空值进入下游。

### 3. 通过 state 传递，不使用全局变量

参考时间作为一次工作流的显式 state 字段传递，沿父图、订单子图和节点边界流转。这样适合并发请求，不会发生不同 session 之间的时间污染。

### 4. CLI 不再缓存 session 初始化时间

保留 `CliSession` 的其他交互状态，但将 reference time 的确定从 session factory 移到每次消息处理开始处。CLI 当前没有外部传入时间的交互命令，因此每轮使用当前 Asia/Shanghai 时间。

## Risks / Trade-offs

- [调用方传入非法时间] → 入口返回明确的请求参数错误，不启动工作流。
- [CLI 和 API 默认值逻辑重复] → 提取共享的时间格式化/校验辅助函数，并通过单元测试保证行为一致。
- [下游接口仍保留旧兼容签名] → 保持 resolver 的兼容参数，但工作流主路径始终传递显式 reference_time。
- [服务跨时区部署] → 明确使用 `Asia/Shanghai`，不依赖机器本地时区。

## Migration Plan

1. 添加请求级时间解析与默认值辅助逻辑。
2. 修改 CLI 和 API 入口，将确定后的值写入 state。
3. 修改 Rewrite/Extract 调用链和测试，验证同一值贯穿所有阶段。
4. 运行完整测试；若需要回滚，只需恢复入口默认值逻辑，订单字段和外部接口保持兼容。
