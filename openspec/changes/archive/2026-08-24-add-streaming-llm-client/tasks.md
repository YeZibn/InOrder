## 1. 流式事件与 transport

- [x] 1.1 定义统一的流式事件/结果类型，覆盖增量文本、完成、失败和 usage/metadata。
- [x] 1.2 为 Chat Completions 实现 SSE 流式请求与 `delta.content` 解析。
- [x] 1.3 为 Responses 实现 SSE 流式请求与 `response.output_text.delta`、完成、失败事件解析。
- [x] 1.4 保持现有非流式请求、思考参数映射和错误归一化行为不变。

## 2. LLMClient 流式 API

- [x] 2.1 增加显式流式调用入口，按顺序触发增量回调并累积完整文本。
- [x] 2.2 实现首个增量前可重试、首个增量后不重试的错误策略。
- [x] 2.3 在正常结束时返回完整 `LLMResponse`，使结构化 resolver 可继续使用。

## 3. CLI 接入

- [x] 3.1 增加流式输出配置，默认保持非流式兼容行为。
- [x] 3.2 将 CLI 的 LLM 输出 observer 改为增量打印，并保留调用边界与最终链路结果。
- [x] 3.3 验证 full、intent、order 三条链路的选择和结果格式不受影响。

## 4. 测试与验证

- [x] 4.1 增加 Chat Completions 流式事件 fixture 和解析测试。
- [x] 4.2 增加 Responses 流式事件 fixture 和解析测试。
- [x] 4.3 增加完成结果、空事件、失败及重试行为测试。
- [x] 4.4 增加 CLI 流式输出和配置开关测试，并在 conda `agent` 环境运行相关测试。

## 5. 流式结构化响应兼容

- [x] 5.1 增加结构化响应前缀清洗工具，仅移除文本开头的 BOM/零宽格式字符。
- [x] 5.2 将意图、Rewrite、Extract 等 JSON 解析入口接入前缀清洗，保持正文内容不变。
- [x] 5.3 增加开头不可见字符和正文内部不可见字符的回归测试，并用真实流式 CLI 场景验证。
