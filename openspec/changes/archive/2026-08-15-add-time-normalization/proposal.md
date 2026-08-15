## Why

extract 已要求输出绝对时间的 `start`/`end`，但当前代码没有校验格式、顺序或时间用途，且固定时刻与时间窗口没有显式区分。建立时间归一化层，可以让下游调度和订单上下文获得稳定、可验证的时间数据。

## What Changes

- 新增时间实体归一化能力，校验 `start`、`end` 及 `context`。
- 统一时间为带 `Asia/Shanghai` 时区的标准格式。
- 根据边界判断时间类型：`fixed`（固定时刻）或 `range`（时间范围）。
- 支持闭区间和单边开区间，拒绝空区间、非法格式及逆序区间。
- 保留原始时间表达，便于展示和诊断。
- 区分 `new_order` 配送时间与 `history` 查询时间，避免历史查询条件写入订单草稿。
- 暂不替换 LLM 的相对时间识别和日期计算逻辑。

## Capabilities

### New Capabilities

- `order-time-normalization`: 对订单时间实体进行结构化校验、分类和用途分流。

### Modified Capabilities

<!-- None -->

## Impact

影响 `extract` 实体处理、订单上下文 reducer 和新增 normalization 模块；不新增外部依赖，不接入 LangGraph 或外部日历服务。
