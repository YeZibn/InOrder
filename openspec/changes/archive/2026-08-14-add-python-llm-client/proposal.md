## Why

项目需要先验证 Python 应用能够稳定调用大语言模型，为后续 LangGraph 拉货下单工作流提供最小可复用基础。目前仓库没有业务代码或统一的模型访问层，直接进入业务流程会把供应商协议、配置和错误处理混入工作流逻辑。

## What Changes

- 新增一个 Python LLM 客户端能力，提供统一的文本对话调用接口。
- 支持通过环境变量配置 API Key、Base URL、模型名、超时和基础重试参数。
- 支持通过可选环境变量配置 reasoning effort（`low`、`medium`、`high`），控制支持该参数的推理模型的思考强度。
- 将供应商响应转换为稳定的应用层响应结构，并保留必要的用量信息。
- 统一处理认证失败、请求超时、限流和其他上游错误。
- 增加 mock 测试与一个最小调用入口，验证配置、请求和响应链路。
- 本阶段不实现拉货领域逻辑、LangGraph 业务节点、流式输出、工具调用或 RAG。

## Capabilities

### New Capabilities

- `llm-client`: 提供 Python 应用调用 OpenAI-compatible 大语言模型接口的能力。

### Modified Capabilities

无。

## Impact

- 新增 Python 项目基础结构、LLM 客户端模块、配置读取和错误类型。
- 引入一个 OpenAI-compatible Python SDK 及测试依赖。
- 客户端调用参数增加可选的 reasoning effort；未配置时不发送该参数，以兼容不支持它的中转站。
- 为后续 LangGraph 节点预留可注入的客户端接口，但不改变现有业务 API（当前暂无业务代码）。
