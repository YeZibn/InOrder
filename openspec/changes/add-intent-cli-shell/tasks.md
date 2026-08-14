## 1. CLI 基础结构

- [x] 1.1 定义 CLI 模式、session 状态和可替换 IO 接口。
- [x] 1.2 实现标准输入循环、提示符和正常退出处理。
- [x] 1.3 增加 `inorder` 项目命令入口，保留现有 `llm-verify`。

## 2. 命令解析与模式切换

- [x] 2.1 实现 `/intent` 无参数交互选择和带参数直接切换。
- [x] 2.2 实现 `/mode`、`/help`、`/clear`、`/exit` 命令。
- [x] 2.3 处理未知命令、非法模式和空输入。

## 3. Graph 适配与输出

- [x] 3.1 实现 `auto` 模式调用编译后的意图 StateGraph。
- [x] 3.2 实现 `order` 模式的订单意图识别入口，保持 recognition-only。
- [x] 3.3 实现 `qa` 模式占位结果和 `plan` 模式结构化计划输出。
- [x] 3.4 实现 IntentPlan、澄清状态和错误的统一文本格式化。

## 4. 测试与文档

- [x] 4.1 编写命令解析和模式切换单元测试。
- [x] 4.2 编写 session `/clear`、`/exit` 和普通消息路由测试。
- [x] 4.3 编写四种模式的 graph adapter mock 测试。
- [x] 4.4 编写 recognition-only 边界测试，确认 CLI 不调用业务工具。
- [x] 4.5 更新 README 的 CLI 使用说明，并在 conda `agent` 环境运行完整测试。

## 5. 范围确认

- [x] 5.1 确认本阶段未实现订单查询、草稿修改、订单创建、确认下单或真实问答。
- [x] 5.2 确认未引入持久化、checkpoint、interrupt、流式输出或终端 UI 框架。
