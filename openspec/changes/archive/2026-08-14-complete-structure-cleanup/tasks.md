## 1. 迁移 LLM 基础设施

- [x] 1.1 将 LLM client、config、errors、models、transport 的真实实现迁移到 `infrastructure/llm/`
- [x] 1.2 修正新 LLM 包内部导入和包级导出
- [x] 1.3 将根目录 LLM 模块改为薄兼容层并删除重复实现

## 2. 迁移意图领域

- [x] 2.1 将 `IntentPlan`、`IntentStep`、规划状态和领域异常迁移到 `intent/models.py`
- [x] 2.2 将 `IntentModel`、`LLMIntentModel` 和结构化响应处理迁移到 `intent/protocols.py`、`intent/resolver.py`
- [x] 2.3 将校验与 planning facade 实现迁移到 `intent/validation.py`、`intent/planning.py`
- [x] 2.4 将 `intent_planning.py` 改为兼容层，删除旧实现重复定义

## 3. 迁移 CLI 与命令入口

- [x] 3.1 将交互 CLI 的会话、解析、格式化和运行循环迁移到 `cli/`
- [x] 3.2 将 LLM verify 与 intent chat 入口实现放入 `commands/`
- [x] 3.3 将根 `cli.py`、`intent_cli.py` 改为薄兼容层，消除模块/包同名冲突
- [x] 3.4 更新 `pyproject.toml` 的 console scripts 和所有内部 import

## 4. 清理与验证

- [x] 4.1 清理不再需要的重复文件、wildcard re-export 和过时缓存文件
- [x] 4.2 增加 source-of-truth 与兼容层边界测试
- [x] 4.3 在 conda `agent` 环境运行全量测试
- [x] 4.4 验证 `inorder`、`llm-verify`、模块导入和 README 示例
