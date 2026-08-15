## Why

当前 extract 只要求手机号实体带有 sender/receiver 角色，没有规定号码格式；reducer 也会直接写入原始文本，导致空格、短横线和国家码表达不一致。增加确定性的手机号归一化，可以在订单上下文中保存稳定且可校验的大陆手机号。

## What Changes

- 明确 phone entity 的归一化输入和输出契约。
- 清理空格、短横线、括号等常见格式字符。
- 支持 `+86` 和 `0086` 前缀，并统一为 11 位大陆手机号。
- 校验归一化结果符合大陆手机号格式，非法号码显式报错，不自动猜测或截断。
- 保留 `raw` 原始表达，将规范号码写入 `value`。
- 接入现有实体归一化与 reducer，保持 set/replace/remove 行为，拒绝 phone 的 add。
- 暂不支持固话、分机、国际号码和号码真实性查询。

## Capabilities

### New Capabilities

- `order-phone-normalization`: 对订单联系人手机号进行格式清理、校验和稳定化。

### Modified Capabilities

<!-- None -->

## Impact

影响 extract 的 phone 输出契约、`normalization` 模块、订单上下文 reducer 和相关测试；不新增外部依赖，不接入外部号码服务。
