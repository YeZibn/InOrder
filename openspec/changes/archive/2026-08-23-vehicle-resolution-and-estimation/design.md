## Context

当前订单子图已完成 Rewrite → Extract → ContextUpdate → CargoProfile；车型归一化可以从集中 `vehicles.json` 产生 canonical code，但尚未有一个节点根据“用户是否提供可匹配车型”决定采用用户车型还是进入估算。

## Goals / Non-Goals

**Goals:**

- 在车型决策中建立用户匹配优先级。
- 将无法匹配或缺失车型的情况统一导向货物画像估算。
- 让估算读取车辆主数据能力字段，但不做用户指定车型的能力校验或自动纠正。
- 将来源、最终车型和原因纳入可序列化的订单图结果。

**Non-Goals:**

- 不输出 `feasible`/`infeasible`/`unknown` 能力校验状态。
- 不对已匹配的用户车型进行替换、推荐或否定。
- 不实现装箱优化、多车拆单、路线价格优化或外部订单业务。

## Decisions

1. **先匹配，再估算。** 精确 catalog 匹配优先；精确失败后复用现有严格 RapidFuzz + n-gram Ensemble。只有未提供车型或 Ensemble 拒绝时才进入估算。
2. **用户匹配结果具有最高优先级。** `user_matched` 结果直接作为最终车型，即使货物画像规模与其能力范围看起来不一致；能力字段只作为估算输入。
3. **估算输出使用 canonical code。** 估算模型只能从 catalog code 中选择，解析层校验 code 合法性，并返回 `estimated` 来源和原因。
4. **不匹配原文不进入 canonical context。** 原始模糊表达可以保存在决策原因/诊断字段，不能覆盖已有 `OrderContext` 车型。
5. **车型节点位于 CargoProfile 之后。** 这样无车型和未匹配车型都可以使用最新的完整货物画像；用户匹配车型则可以短路估算。

## Risks / Trade-offs

- [估算模型可能选择不合理车型] → 只允许返回主数据中的 canonical code，并覆盖非法/未知 code 校验。
- [用户表达与 canonical context 的动作关系复杂] → 继续使用现有 entity action 和归一化边界，未匹配输入不得写入 context。
- [用户匹配车型可能实际装不下货物] → 按用户决策明确不做能力校验，本 change 只保留用户选择。

## Migration Plan

1. 新增车型决策结果模型和估算 resolver/node。
2. 将订单图在 CargoProfile 后接入车型解析节点，并扩展状态/CLI 展示。
3. 增加用户匹配、无车型、模糊车型回退和非法估算 code 测试。
4. 运行完整测试；保留现有车型归一化 API 和 cargo profile 契约。
