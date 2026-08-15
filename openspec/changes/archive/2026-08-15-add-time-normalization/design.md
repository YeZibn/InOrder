## Context

extract prompt 已要求输出 `start`、`end` 和 `context`，但目前解析层与 reducer 未对时间边界做代码校验，也没有区分固定时刻和时间范围。时间归一化需要复用现有 Entity 管道，同时避免承担自然语言相对时间识别。

## Goals / Non-Goals

**Goals:**

- 将 extract 的时间边界解析为带 `Asia/Shanghai` 时区的稳定格式。
- 校验闭区间、单边开区间、边界顺序和 context。
- 增加 `kind=fixed|range`，保留 start/end 与 raw。
- 让 history 时间不进入当前订单 delivery_time。

**Non-Goals:**

- 不重写 LLM 的相对时间识别、星期计算或节假日推理。
- 不接入外部日历、时区数据库或 LangGraph。
- 不在本次变更中设计历史订单查询服务。

## Decisions

### 使用带时区 ISO 格式作为内部时间值

输入兼容 extract 当前的 `YYYY-MM-DD HH:MM`，输出统一为 `YYYY-MM-DDTHH:MM:SS+08:00`。选择显式时区而不是继续保存 naive 字符串，是为了避免跨服务或跨环境解释不一致。

### 通过边界推导 kind

`start == end` 且两者存在时为 `fixed`；只要边界不同或存在单边缺失即为 `range`。保留 start/end 而不改成单独的 `at` 字段，以兼容当前 extract 和上下文模型。

### 归一化与分流分离

Normalizer 只在时间实体上写入规范字段和 kind；reducer 在处理 `new_order` 时写入 delivery_time，遇到 `history` 时拒绝覆盖订单配送时间并返回明确的上下文错误。这样不会把历史查询逻辑塞进时间解析器。

### 保守处理边界缺失

允许单边开区间，拒绝双边缺失。不会根据缺失边界猜测全天、具体时刻或默认时间。

## Risks / Trade-offs

- [LLM 计算的相对日期可能错误] → 归一化只校验结果；后续可独立替换为代码计算。
- [现有调用方依赖无时区字符串] → 第一版保留 start/end 语义并在测试中明确新格式，必要时提供兼容解析。
- [history 时间进入 reducer] → 在 reducer 边界增加 context 分流和测试。
