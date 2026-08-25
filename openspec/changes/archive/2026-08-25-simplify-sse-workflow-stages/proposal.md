## Why

当前 SSE 将 rewrite、extract、context update 等内部节点直接映射为对外阶段，客户端需要理解实现细节才能展示流程，信息过载且容易受内部图结构变化影响。需要收敛为稳定的业务阶段，只让用户看到意图识别、订单处理、货物画像和车型处理。

## What Changes

- 将 `THINKING_STEP` 的公开阶段收敛为 `intent`、`order`、`cargo_profile` 和 `vehicle`。
- 将 rewrite、extract、订单上下文合并归并到“处理订单”阶段，不再单独对外发送。
- 保留 `THINKING_START`、`THINKING_DONE`、`CREATE_ORDER_CONTEXT`、`DONE` 和 `ERROR` 事件契约。
- 保持 LangGraph 父子图和内部节点执行顺序不变，仅调整 SSE 对外事件映射。
- 保持现有 CLI、同步 MainGraph 结果和 SSE 请求接口兼容。

## Capabilities

### New Capabilities

### Modified Capabilities

- `workflow-sse-events`: 收敛工作流阶段事件的公开粒度，隐藏订单子图内部处理节点。
- `main-parent-graph`: 更新父图生命周期事件对外展示要求，保持父子图边界和同步结果兼容。

## Impact

- 修改 `WorkflowEventAdapter` 的阶段映射与回退逻辑。
- 更新 SSE 事件相关测试和主规格。
- 不新增依赖，不改变 `/api/v2/chat` 请求格式，不影响 `inorder` CLI。
