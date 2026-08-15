## Why

当前 extract 可能返回中文自然语言枚举，也可能返回已经归一化的数值或 code；如果直接交给 reducer，订单上下文会出现格式不稳定和非法值。现在建立独立的枚举归一化层，可以在不接入 LangGraph 的前提下，为后续上下文合并提供稳定输入。

## What Changes

- 新增订单枚举归一化能力，处理支付方式、发票类型、本人跟车标记和服务类型。
- 支持中文表达、已归一化值和常见同义表达的幂等转换。
- 对未知或不支持的枚举值显式报告归一化错误，不静默猜测。
- 在 extract 与 `OrderContextReducer` 之间提供可独立调用的归一化接口。
- 暂不处理车型、跟车人数、度量单位和货物属性推断。

## Capabilities

### New Capabilities

- `order-enum-normalization`: 将订单相关枚举表达转换为稳定的内部值。

### Modified Capabilities

<!-- None -->

## Impact

影响 `extract` 实体处理、订单上下文 reducer 和新增的 normalization 模块；不新增外部依赖，不改变 LangGraph 接入方式。
