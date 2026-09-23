# llm-client Specification

## Purpose

为 Python 应用提供一个可配置、可测试且与具体业务解耦的大语言模型文本调用能力，作为后续 LangGraph 工作流的基础设施。

## Requirements

### Requirement: Load and validate client configuration

系统 SHALL 从运行时配置中读取模型服务的 API key、provider、base URL、模型标识和可选的 `LLM_API_MODE`；provider SHALL 为 `openai` 或 `deepseek`，接口模式 SHALL 为 `chat_completions` 或 `responses`。未配置 provider 时默认为 `openai`；缺少必需配置或配置值非法时 SHALL 拒绝发起请求并返回明确的配置错误。系统 SHALL 支持可选的 provider-compatible reasoning effort；DeepSeek V4 思考模式启用后 reasoning_effort 仅接受 `high`/`max`，且 `thinking` 参数与 `reasoning_content` 解析不在本变更范围。

#### Scenario: Valid configuration
- **WHEN** API key、base URL 和模型标识均已配置
- **THEN** 客户端使用这些配置向模型服务发起请求

#### Scenario: Missing required configuration
- **WHEN** API key、base URL 或模型标识缺失
- **THEN** 客户端不发起上游请求并返回可识别的配置错误

#### Scenario: Valid reasoning effort
- **WHEN** reasoning effort 配置为 `low`、`medium` 或 `high`
- **THEN** 客户端将该值保存到运行时配置，供支持该参数的模型调用使用

#### Scenario: Invalid reasoning effort
- **WHEN** reasoning effort 配置为其他值
- **THEN** 客户端不发起上游请求并返回配置错误

#### Scenario: Select API mode
- **WHEN** `LLM_API_MODE` 设置为 `chat_completions` 或 `responses`
- **THEN** 客户端使用对应的上游接口；未设置时使用 `chat_completions`

#### Scenario: Invalid API mode
- **WHEN** `LLM_API_MODE` 设置为其他值
- **THEN** 客户端不发起上游请求并返回配置错误

#### Scenario: Load a valid DeepSeek configuration

- **WHEN** 配置包含 `LLM_PROVIDER=deepseek`、API key、base URL（或默认地址）和模型
- **THEN** 客户端成功加载配置并保留 provider、接口模式和模型信息

#### Scenario: Reject unsupported provider

- **WHEN** `LLM_PROVIDER` 不是 `openai` 或 `deepseek`
- **THEN** 配置加载失败并返回配置错误，不创建可调用客户端

#### Scenario: Preserve existing OpenAI defaults

- **WHEN** 未配置 `LLM_PROVIDER`
- **THEN** 客户端按 `openai` provider 和既有默认接口模式加载

### Requirement: Select an upstream API mode

系统 SHALL 根据 `LLM_API_MODE` 选择 Chat Completions 或 Responses API；未设置时使用 `chat_completions`。provider 不得覆盖调用方显式选择的 API mode。

#### Scenario: Use DeepSeek Chat Completions

- **WHEN** provider 为 `deepseek` 且 API mode 为 `chat_completions`
- **THEN** 客户端使用 DeepSeek 兼容的 messages 请求和 Chat Completions 响应归一化

#### Scenario: Use DeepSeek Responses

- **WHEN** provider 为 `deepseek` 且 API mode 为 `responses`
- **THEN** 客户端使用 DeepSeek Responses 的 input 请求和 output text 响应归一化

### Requirement: Text chat completion

系统 SHALL 接受包含角色和文本内容的消息列表，并根据 API 模式返回统一结构的文本结果；调用方无需依赖供应商特定的响应对象。

#### Scenario: Successful completion
- **WHEN** 调用方提供有效消息列表且上游返回成功
- **THEN** 系统返回生成文本、模型标识以及可用的 token 使用量

#### Scenario: Empty messages
- **WHEN** 调用方提供空消息列表
- **THEN** 系统在发起请求前返回参数错误

#### Scenario: Reasoning effort is forwarded when configured
- **WHEN** 调用方使用已配置 reasoning effort 的客户端发送消息
- **THEN** 客户端向所选接口传递对应格式的 reasoning effort 参数

#### Scenario: Reasoning effort is omitted when unset
- **WHEN** 调用方未配置 reasoning effort
- **THEN** 客户端不向上游请求添加该可选参数

### Requirement: Upstream error normalization

系统 SHALL 将认证失败、限流、超时和其他上游失败转换为稳定且可区分的应用层错误类型，并保留安全的诊断信息。

#### Scenario: Authentication failure
- **WHEN** 上游因 API key 无效返回认证错误
- **THEN** 系统返回认证类错误，且错误信息不得包含 API key

#### Scenario: Request timeout
- **WHEN** 上游请求超过配置的超时时间
- **THEN** 系统返回超时类错误，并按照配置执行有限次数的重试

#### Scenario: Rate limited
- **WHEN** 上游返回限流错误
- **THEN** 系统返回限流类错误，并暴露可选的重试等待信息

### Requirement: Provide asynchronous LLM calls alongside synchronous calls

LLM 客户端 SHALL 提供非阻塞的异步完整调用与配置驱动的异步流式调用，覆盖现有 Chat Completions 和 Responses 两种接口模式，并返回与同步入口等价的规范化完整结果。现有同步入口 SHALL 继续可用于 CLI 和其他同步调用方；异步流式调用不改变工作流对外的节点级 SSE 协议。

#### Scenario: Async completion returns normalized result
- **WHEN** 异步工作流调用模型且上游返回成功
- **THEN** 调用方获得与同步入口同形的文本、模型和可用 usage，等待期间事件循环可处理其他请求

#### Scenario: Async model streaming returns a complete result
- **WHEN** 配置启用模型流式调用且异步工作流选择 Chat Completions 或 Responses
- **THEN** 客户端异步消费内容增量并返回完整的规范化结果，不把 token 增量直接发送为工作流 SSE 事件

#### Scenario: Existing synchronous caller remains supported
- **WHEN** CLI 通过现有同步调用入口请求模型
- **THEN** 客户端继续按既有返回类型与错误类型返回结果

### Requirement: Handle transient upstream failures

LLM 客户端 SHALL 仅对网络失败、请求超时、限流和 5xx 上游错误进行有限重试；鉴权、配置、参数和模型不存在错误 SHALL 不重试。一次逻辑调用 SHALL 最多发出配置允许的实际上游请求次数，且异步重试等待不得阻塞事件循环。有效 `Retry-After` SHALL 在剩余时间允许时得到遵守；若等待将超过工作流 deadline，系统 SHALL 停止重试。

#### Scenario: Retry a transient failure
- **WHEN** LLM 请求遇到超时、429 或 5xx 错误
- **THEN** 客户端在配置的次数、退避上限和剩余预算内重试，最终成功则只返回一个规范化响应

#### Scenario: Stop on fatal failure
- **WHEN** LLM 请求遇到 400、401、403 或配置错误
- **THEN** 客户端不重试并返回稳定的应用层错误

#### Scenario: Honor a feasible retry delay
- **WHEN** 上游返回可重试限流错误及有效 `Retry-After`，且等待后仍有工作流预算
- **THEN** 客户端至少等待该时长后再重试，且不超过总重试次数

#### Scenario: Stop retrying at the deadline
- **WHEN** 调用方提供的工作流 deadline 已到达，或计划中的有效 `Retry-After` 等待将越过该 deadline
- **THEN** 客户端不再启动新请求，并向工作流报告超时

### Requirement: Separate transport and output retries

LLM 客户端 SHALL 将传输重试与 resolver 的结构化输出修复重试分开，传输层成功返回后不得因输出解析失败而在底层无限重放请求。

#### Scenario: Malformed structured output
- **WHEN** 上游请求成功但内容为空、JSON 非法或不符合结构约束
- **THEN** resolver 最多发起一次带格式修复要求的后续请求，仍失败则向工作流返回错误

### Requirement: Testable integration boundary

系统 SHALL 提供可注入或可替换的模型调用边界，使单元测试能够在不访问真实模型服务的情况下验证成功和失败路径。

#### Scenario: Mocked successful call
- **WHEN** 测试注入一个模拟模型服务并发送有效请求
- **THEN** 测试能够验证请求参数映射和统一响应结果

#### Scenario: Mocked upstream failure
- **WHEN** 模拟模型服务返回超时或上游错误
- **THEN** 测试能够验证对应的应用层错误类型和重试行为

### Requirement: Minimal verification entry point

系统 SHALL 提供一个最小调用入口，用于在配置正确时发送一条文本消息并输出结果，在配置缺失或调用失败时输出非敏感错误信息和非零退出状态。

#### Scenario: Run verification with valid configuration
- **WHEN** 用户使用有效环境变量运行验证入口
- **THEN** 入口输出模型生成的文本结果并以成功状态退出

#### Scenario: Run verification without configuration
- **WHEN** 用户未配置必需环境变量运行验证入口
- **THEN** 入口提示缺少配置并以非零状态退出

### Requirement: Streaming LLM calls

LLM 客户端 SHALL 根据配置调用 Chat Completions 或 Responses，并将供应商的流式响应归一化为增量文本和完整 `LLMResponse`；既有完整调用入口 SHALL 保持兼容。

#### Scenario: Configured Chat Completions streaming call
- **WHEN** API 模式为 `chat_completions` 且调用方请求流式调用
- **THEN** 客户端调用 Chat Completions，使用 `reasoning_effort` 参数格式，并按顺序交付 `delta.content`

#### Scenario: Configured Responses streaming call
- **WHEN** API 模式为 `responses` 且调用方请求流式调用
- **THEN** 客户端调用 Responses，使用 `reasoning.effort` 参数格式，并按顺序交付文本增量事件

#### Scenario: Streaming complete result
- **WHEN** 流式响应正常完成
- **THEN** 客户端返回所有增量拼接后的完整 `LLMResponse`，供结构化 resolver 使用

#### Scenario: Streaming retry boundary
- **WHEN** 首个文本增量到达前发生可重试的上游错误
- **THEN** 客户端按现有重试策略重试；如果已经交付文本增量后发生错误，则终止本次请求且不得重复重试

#### Scenario: Structured response prefix
- **WHEN** 流式完整文本开头包含 BOM 或零宽格式字符
- **THEN** 结构化 JSON 解析清理开头字符并保留正文内容
