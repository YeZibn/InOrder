## Why

当前订单实体提取对 `location` 只保留城市字段，无法支持物流实际需要的园区、仓库、门店等具体装卸地址。现在补充一个受控的完整地址字段，在保留城市级信息的同时保存用户明确提供的地址原文。

## What Changes

- 扩展 `location` 实体属性，保留 `city` 和 `full_address` 两个地址粒度。
- 要求 pickup/dropoff 均可提取用户明确表达的完整地址。
- 没有详细地址时允许 `full_address` 使用城市表达；没有明确城市时不猜测城市。
- 更新 JSON 提取 prompt、LangExtract prompt 描述、few-shot 示例和相关测试。
- 保持地址角色判断、action 语义和原文 grounded 提取规则不变。
- 不引入地址库补全、行政区拆分、地理编码、经纬度或路线计算。

## Capabilities

### New Capabilities

<!-- None. This change modifies an existing extraction capability. -->

### Modified Capabilities

- `order-entity-extraction`: location 实体从仅城市扩展为城市与完整地址两层属性。

## Impact

- 影响 `src/inorder_llm/extract/resolver.py` 中的 location prompt、示例和 JSON 契约。
- 影响 LangExtract location attributes 的测试与映射验证。
- `OrderContext.pickup_location` 和 `dropoff_location` 已是可序列化映射，可兼容新增字段；不改变 reducer 的角色路由。
- 不新增运行时依赖，不改变其他实体类型和订单链路结构。
