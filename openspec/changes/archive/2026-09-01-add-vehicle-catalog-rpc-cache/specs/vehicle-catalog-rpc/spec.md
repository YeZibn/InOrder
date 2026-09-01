## Purpose

为订单服务提供按城市查询、版本化和可回退的车型主数据访问能力，使车型数据能够由独立服务统一维护，同时保证本地缓存和远程服务故障时下单链路仍可用。

## ADDED Requirements

### Requirement: Provide city-aware vehicle catalog

车型目录服务 SHALL 接受标准化城市和回退选项，返回车型、特殊规格、数据来源及目录版本；城市覆盖数据不存在时 SHALL 返回全国默认目录。

#### Scenario: Query city override
- **WHEN** 请求城市存在城市车型覆盖
- **THEN** 返回该城市车型数据，并标记 `source=city_override`

#### Scenario: Fall back to global catalog
- **WHEN** 请求城市没有覆盖数据
- **THEN** 返回全国默认车型数据，并标记 `source=global_default`

### Requirement: Cache catalog snapshots locally

Python 服务 SHALL 缓存按城市和版本标识的不可变目录快照，并在快照有效期内优先使用缓存而不调用远程服务。

#### Scenario: Serve a fresh cache hit
- **WHEN** 城市目录快照存在且未过期
- **THEN** 直接返回缓存快照及其版本信息

### Requirement: Coordinate concurrent refreshes

目录缓存刷新 SHALL 支持城市级并发锁和双重检查，同一城市同时发生多个缓存未命中时最多发起一次远程刷新请求。

#### Scenario: Collapse concurrent misses
- **WHEN** 多个请求同时刷新同一城市
- **THEN** 一个请求执行 RPC，其余请求等待后复用新快照

### Requirement: Degrade on catalog service failure

远程目录调用 SHALL 具有短超时和有限重试；失败时优先使用未过期或过期的旧城市缓存，其次使用本地全国默认快照，不得直接导致订单工作流失败。

#### Scenario: Use stale cache after RPC failure
- **WHEN** 城市缓存已过期且 RPC 调用失败
- **THEN** 返回旧缓存并标记 `catalog_stale=true`

#### Scenario: Use local fallback on cold start
- **WHEN** RPC 失败且没有城市缓存
- **THEN** 返回本地全国默认目录并标记 `source=local_fallback`
