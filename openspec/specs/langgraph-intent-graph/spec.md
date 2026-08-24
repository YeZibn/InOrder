# langgraph-intent-graph Specification

## Purpose

为意图识别提供真正基于 LangGraph StateGraph 的主意图、子意图和条件路由骨架，使后续业务图可以稳定嵌入并消费统一的意图计划结果。

## Requirements

### Requirement: Compiled LangGraph entry point

系统 SHALL 提供一个可编译并可调用的 LangGraph StateGraph 入口，接收用户消息和可注入的意图识别器，返回统一的意图图状态。

#### Scenario: Graph compiles and invokes
- **WHEN** 调用方使用 mock 意图识别器构建并调用图
- **THEN** 图成功编译、执行并返回包含主意图或澄清状态的结果

### Requirement: Separate main and sub intent nodes

图 SHALL 将主意图识别和订单子意图识别注册为两个独立节点；子意图节点不得在主意图不是 `order` 时执行。

#### Scenario: Order enters sub-intent node
- **WHEN** 主意图节点输出 `order`
- **THEN** 图路由到子意图节点并继续构建订单意图计划

#### Scenario: QA bypasses sub-intent node
- **WHEN** 主意图节点输出 `qa`
- **THEN** 图不执行子意图节点并返回空订单子意图计划

### Requirement: Conditional main-intent routing

图 SHALL 根据主意图在 `order` 和 `qa` 两个分支之间路由；不得注册或执行 `ambiguous` 分支。

#### Scenario: Order enters sub-intent node
- **WHEN** 主意图节点输出 `order`
- **THEN** 图路由到子意图节点并继续构建订单意图计划

#### Scenario: QA bypasses sub-intent node
- **WHEN** 主意图节点输出 `qa`
- **THEN** 图不执行子意图节点并返回空订单子意图计划

### Requirement: Unified graph output

所有分支 SHALL 通过统一出口返回包含 `order` 或 `qa` 主意图、子意图计划和澄清状态的状态结构。

#### Scenario: Two branches share one output
- **WHEN** 图处理 order 或 qa 请求
- **THEN** 两条路径都通过统一出口返回相同字段结构

### Requirement: Skeleton-only boundary

图骨架 SHALL 只负责节点编排、路由和计划结构传递，不得调用订单查询、草稿修改、创建订单、确认下单或问答业务工具。

#### Scenario: No business side effect
- **WHEN** 图识别出任意订单子意图
- **THEN** 图只返回识别状态，不产生业务数据读写或外部业务调用

### Requirement: Parent graph embeddable intent subgraph

意图图 SHALL 可独立调用，也 SHALL 能作为 MainGraph 的子图挂载；输出必须包含父图路由所需的 `main_intent` 和经过校验的 `intent_plan`。

#### Scenario: Parent graph consumes intent output
- **WHEN** MainGraph 调用意图图
- **THEN** 意图图输出 `main_intent` 和 `intent_plan` 供父图路由

#### Scenario: Recognition-only boundary is preserved
- **WHEN** 意图图独立或被父图调用
- **THEN** 意图图只执行意图识别和计划校验，不查询或修改真实订单
