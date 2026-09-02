## Why

当前地址实体只有 `city` 和 `full_address`，省级信息只能埋在完整地址原文中，城市目录、区域服务和后续地理能力无法直接使用。增加可选 `province` 字段可以提升地址结构化程度，同时保持不完整地址和原文可追溯性。

## What Changes

- location 实体增加可选 `province` 字段。
- province 仅在用户原文明确出现时提取，不允许模型根据城市常识补全。
- 保持 `city`、`full_address`、`role` 和原始地址边界规则不变。
- 将 province 透传到 OrderContext、API 响应和地址摘要。
- 增加省级字段提取、缺失和原文边界测试。

## Capabilities

### New Capabilities

### Modified Capabilities

- `order-entity-extraction`: location 支持可选省份字段及明确来源约束。
- `conversation-order-context`: 订单上下文地址保存 province。

## Impact

- 影响 LangExtract/JSON 提取 Prompt、location adapter、上下文 reducer 和相关测试。
- 不改变车型城市选择优先级；车型仍以起点 city 为主，province 作为扩展信息。
- 不增加区、街道、门牌号等更细地址字段，也不引入自动地理编码。
