## Context

当前新目录中的多数文件仍是旧模块的 re-export，真实实现还在包根目录。CLI 还存在 `cli.py`、`intent_cli.py` 与 `cli/` 并存的命名冲突。本次设计以“先移动实现、再建立兼容层、最后清理重复文件”为迁移顺序。

## Goals / Non-Goals

**Goals:**

- 让 `infrastructure/llm/`、`intent/` 和 `cli/` 承载唯一真实实现。
- 让旧模块最多只包含显式兼容导入，不再包含业务逻辑。
- 消除 `cli.py` 与 `cli/` 的模块/包冲突，统一两个 console script 的目标。
- 保证旧公共 import、LangGraph 图输出和 CLI 行为兼容。

**Non-Goals:**

- 不改变意图识别协议、状态字段和节点拓扑。
- 不迁移顶层包名 `inorder_llm`。
- 不删除仍被声明为公共兼容路径的旧模块，除非已确认无兼容需要。

## Decisions

### 以新目录为 source of truth

先把根目录实现内容移动并改写 import，使新目录成为唯一实现；旧模块只保留显式 re-export。相比继续在旧文件上迭代，这能避免两个实现逐渐漂移。

### LLM 模块按文件真实迁移

`client.py`、`config.py`、`errors.py`、`models.py`、`transport.py` 的内容移动至 `infrastructure/llm/`，内部引用统一改为同包相对导入。根目录同名文件改成兼容层。

### 意图领域拆分为模型、协议、resolver、planning、validation

从旧 `intent_planning.py` 按职责拆分实现，而不是继续通过 wildcard re-export。`IntentPlan` 与 `IntentStep` 只在 `intent/models.py` 定义，LLM 适配器只在 `intent/resolver.py` 定义。

### CLI 以 `cli/app.py` 为主实现

将交互会话、命令解析、格式化实现移入 `cli/`；LLM 验证逻辑放入 `commands/llm_verify.py`，intent 交互入口放入 `commands/intent_chat.py`。根 `cli.py` 和 `intent_cli.py` 仅保留兼容入口，避免删除已有 import 造成不必要破坏。

### 用测试锁定迁移边界

增加测试确保新路径包含真实实现、旧路径不包含重复定义，并验证旧 import 与两个 console script 仍可用。

## Risks / Trade-offs

- [旧内部 import 遗漏] → 迁移后用 `rg` 检查根实现文件，并运行全量测试和模块导入测试。
- [相对导入循环] → 保持依赖方向为 `commands/cli → graph/intent → infrastructure`，LLM 基础设施不导入上层。
- [兼容层长期残留] → 在兼容模块中加明确 docstring，后续可单独提出删除 change。
- [脚本入口短期变化] → 保留原 script 名称，仅更换目标函数并进行 `--help` 冒烟验证。

## Migration Plan

1. 将 LLM 和 intent 实现复制/移动到目标目录并修正内部导入。
2. 将 CLI 实现移动到 `cli/app.py` 与 `commands/`。
3. 把旧文件改成薄兼容层，删除重复定义和冲突入口。
4. 更新 `pyproject.toml`、测试、README。
5. 在 conda `agent` 环境运行测试、导入检查和 CLI 冒烟。
6. 如失败，依据兼容层回退到旧入口；不涉及数据迁移。
