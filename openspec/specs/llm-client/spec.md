# llm-client Specification

## Purpose

为 Python 应用提供一个可配置、可测试且与具体业务解耦的大语言模型文本调用能力，作为后续 LangGraph 工作流的基础设施。

## Requirements

### Requirement: Configurable model access

系统 SHALL 从运行时配置中读取模型服务的 API key、base URL 和模型标识，并支持可选的 reasoning effort。缺少必需配置或 reasoning effort 非 `low`、`medium`、`high` 时，系统 SHALL 拒绝发起请求并返回明确的配置错误。

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

### Requirement: Text chat completion

系统 SHALL 接受包含角色和文本内容的消息列表，并返回统一结构的文本结果；调用方无需依赖供应商特定的响应对象。

#### Scenario: Successful completion
- **WHEN** 调用方提供有效消息列表且上游返回成功
- **THEN** 系统返回生成文本、模型标识以及可用的 token 使用量

#### Scenario: Empty messages
- **WHEN** 调用方提供空消息列表
- **THEN** 系统在发起请求前返回参数错误

#### Scenario: Reasoning effort is forwarded when configured
- **WHEN** 调用方使用已配置 reasoning effort 的客户端发送消息
- **THEN** 客户端向上游请求传递对应的 `reasoning_effort` 参数

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
