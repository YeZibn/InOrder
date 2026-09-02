## Context

当前 location 实体和 OrderContext 只保存 `role`、`city`、`full_address`。地址提取要求保持原文 grounded，车型目录主要使用 city；新增 province 需要扩展字段但不改变现有城市选择逻辑。

## Goals / Non-Goals

**Goals:**

- 在提取和上下文中保存明确出现的省份。
- 保证 province 与 city、full_address 同源且可回溯。
- 对旧请求和未提供省份的地址保持兼容。

**Non-Goals:**

- 不通过城市反查省份。
- 不引入地理编码或行政区数据库。
- 不拆分区、街道、门牌号等更细地址层级。

## Decisions

1. province 作为 location attributes 的可选字符串，与 city 同级；提取 Prompt 和 adapter 只校验类型及原文边界，不负责推断。
2. province 输出去除“省”等行政区后缀，但 `full_address` 保留用户连续原文；只有原文明确出现省级表达时才填充。
3. OrderContext 直接透传 province，旧上下文缺失该键时按 `None` 兼容；车型有效城市仍以 pickup city 为主。
4. LangExtract 和 JSON 两条提取路径使用同一字段契约和 few-shot，避免后端结果不一致。

## Risks / Trade-offs

- [模型可能根据城市常识补省份] → Prompt 明确禁止推断，并增加 province 缺失测试。
- [历史上下文没有 province] → 读取时默认空值，不进行回填。
- [行政区后缀处理不一致] → 只在业务属性中去后缀，完整地址始终保留原文。

## Migration Plan

1. 扩展 location Prompt、examples、adapter 和 OrderContext reducer。
2. 增加 API/CLI 序列化兼容测试。
3. 发布后旧请求无需变更；新请求可逐步携带 province。
