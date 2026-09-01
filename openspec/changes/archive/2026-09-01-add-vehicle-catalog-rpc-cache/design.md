## Context

当前 `vehicles.json` 同时承担车型关键词、归一化和确定性估算的数据来源。新设计保留其为本地全国默认快照，并在其上增加统一 Provider；远程车型服务提供按城市覆盖的数据，Python 订单流程继续负责匹配和极点计算。

## Goals / Non-Goals

**Goals:**

- 统一所有车型相关模块的数据访问入口。
- 支持起点城市优先、用户定位城市兜底和全国默认回退。
- 通过短超时、内存快照、城市级锁和 single-flight 刷新保证低延迟与可用性。
- 记录目录来源、版本和过期状态，便于诊断。

**Non-Goals:**

- Python 不负责维护城市主数据的编辑和发布。
- RPC 服务不执行车型推荐、货物装箱或 LLM 推理。
- 第一版不引入跨进程分布式锁；进程内锁只解决单个 Python 实例并发刷新。

## Decisions

1. **Provider 抽象**：定义统一目录读取协议，保留本地 JSON Provider，并新增 RPC Provider。匹配、归一化、Prompt 词汇、Context reducer 和车型估算均依赖协议，避免模块直接读取文件或调用 RPC。

2. **城市优先级**：由订单处理入口计算 `effective_city`：`pickup_location.city` → `user_location.city` → `None`。城市标准化使用确定性规则；车型目录服务返回实际命中的 `source` 和 `data_version`。

3. **RPC 传输**：Provider 层屏蔽 HTTP JSON 或 gRPC 差异，接口至少支持 `get_catalog(city, fallback=True)`。超时约 0.5–1 秒，最多重试一次；调用失败不向上抛出为订单错误，交由缓存回退处理。

4. **缓存与锁**：使用进程内按城市的不可变快照缓存，缓存项保存加载时间、TTL、版本和来源。读取先无锁检查；未命中或过期时获取城市级 `RLock`，加锁后双重检查，仅首个请求执行刷新，其余请求复用结果。

5. **降级顺序**：新鲜城市缓存 → RPC 城市数据 → 过期城市缓存（标记 `catalog_stale`）→ 本地全国默认快照（标记 `local_fallback`）。所有快照替换均为单次引用替换，避免读到半更新数据。

6. **结果溯源**：扩展车型解析结果的非破坏性元数据，包括 `effective_city`、`vehicle_data_source`、`catalog_version` 和 `catalog_stale`；既有 `source=user_matched|estimated` 语义不变。

## Risks / Trade-offs

- [城市覆盖数据与本地关键词版本不一致] → 所有模块统一使用同一 Provider 快照，并在响应中携带版本。
- [单实例缓存无法跨 Python 进程共享] → 允许每个实例独立缓存；后续规模化时可替换为 Redis，不改变 Provider 契约。
- [过期数据可能不符合最新城市规则] → 标记 `catalog_stale`，设置最大 stale TTL，并在后台/下一请求尝试刷新。
- [RPC 抖动增加首请求延迟] → 使用短超时、单次重试和本地全国快照兜底。

## Migration Plan

1. 先封装现有 `vehicles.json` 为 Local Provider，确保现有行为和测试不变。
2. 增加城市标准化、内存缓存和刷新协调器，并通过依赖注入接入车型解析。
3. 增加 RPC Provider 与环境配置，默认仍启用本地 Provider。
4. 将城市定位字段接入 API 请求，逐步开启城市目录覆盖。
5. 观察 RPC 错误率、缓存命中率和 fallback 比例后，再将远程 Provider 设为默认。
6. 回滚时切回 Local Provider，不需要迁移订单上下文或历史数据。
