## MODIFIED Requirements

### Requirement: Handle transient upstream failures

LLM 客户端 SHALL 仅对网络失败、请求超时、限流和 5xx 上游错误进行有限重试；鉴权、配置、参数和模型不存在错误 SHALL 不重试。

#### Scenario: Retry a transient failure
- **WHEN** LLM 请求遇到超时、429 或 5xx 错误
- **THEN** 客户端在配置的次数和退避上限内重试，最终成功则只返回一个规范化响应

#### Scenario: Stop on fatal failure
- **WHEN** LLM 请求遇到 400、401、403 或配置错误
- **THEN** 客户端不重试并返回稳定的应用层错误

### Requirement: Separate transport and output retries

LLM 客户端 SHALL 将传输重试与 resolver 的结构化输出修复重试分开，传输层成功返回后不得因输出解析失败而在底层无限重放请求。

#### Scenario: Malformed structured output
- **WHEN** 上游请求成功但内容为空、JSON 非法或不符合结构约束
- **THEN** resolver 最多发起一次带格式修复要求的后续请求，仍失败则向工作流返回错误
