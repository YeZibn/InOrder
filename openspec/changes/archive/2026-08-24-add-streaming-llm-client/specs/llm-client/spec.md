## MODIFIED Requirements

### Requirement: LLM client calls configured provider
LLM 客户端 MUST 根据配置调用 Chat Completions 或 Responses，并将供应商响应归一化为统一的 `LLMResponse`；除完整调用外，客户端 MUST 支持可选的流式调用，且不得破坏现有 `chat` 调用方。

#### Scenario: Configured Chat Completions call
- **WHEN** API 模式为 `chat_completions`
- **THEN** 客户端 MUST 调用 Chat Completions，并使用该接口对应的思考参数格式

#### Scenario: Configured Responses call
- **WHEN** API 模式为 `responses`
- **THEN** 客户端 MUST 调用 Responses，并使用 `reasoning.effort` 形式传递思考强度

#### Scenario: Existing complete call
- **WHEN** 调用方使用既有完整调用入口
- **THEN** 客户端 MUST 返回完整 `LLMResponse`，行为与流式功能加入前兼容

#### Scenario: Optional streaming call
- **WHEN** 调用方明确请求流式调用
- **THEN** 客户端 MUST 通过统一增量事件回调交付内容，并在结束后返回完整 `LLMResponse`
