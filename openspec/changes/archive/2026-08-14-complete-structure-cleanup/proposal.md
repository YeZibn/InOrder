## Why

上一个结构重构只建立了新目录和兼容转发，旧目录仍然承载真实实现，导致项目同时存在两套实现和同名模块。现在需要完成物理迁移，让新目录成为唯一源码位置，并把旧路径收敛为明确、可审计的兼容层。

## What Changes

- 将 LLM 基础设施的真实实现移动到 `infrastructure/llm/`。
- 将意图领域模型、协议、校验和 resolver 的真实实现移动到 `intent/`。
- 将交互 CLI 的真实实现移动到 `cli/`，将 LLM 验证和 intent chat 入口放入 `commands/`。
- 删除或改造旧根目录重复实现文件，旧导入路径最多保留薄兼容模块。
- 更新所有内部 import、测试、README 和打包入口，避免 `cli.py` 与 `cli/` 等同名冲突。
- 保持现有 API、LangGraph 行为、CLI 命令和 recognition-only 边界不变。

## Capabilities

### New Capabilities

无。本 change 是实现位置清理和重复代码删除，不改变外部行为，因此通过 `skip_specs: true` 跳过 delta spec。

### Modified Capabilities

无。

## Impact

- 影响 `src/inorder_llm/` 全部模块、测试、README 和 `pyproject.toml`。
- 兼容路径 `inorder_llm.client`、`inorder_llm.intent_planning`、`inorder_llm.intent_cli` 等将视迁移策略保留为薄转发，或在无内部引用后删除。
- 不新增依赖；继续使用 conda `agent` 环境验证。
