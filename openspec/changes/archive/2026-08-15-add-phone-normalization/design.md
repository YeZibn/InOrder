## Context

当前 extract 只声明 phone 的 sender/receiver 角色，手机号文本没有格式契约；现有 normalization 已能处理枚举和时间，reducer 对 phone 直接读取 value 或 extraction_text。手机号归一化应沿用该纯函数管道。

## Goals / Non-Goals

**Goals:**

- 支持常见分隔符和中国大陆国际前缀的清理。
- 用稳定的 11 位字符串作为内部 value，并保留 raw。
- 对非法号码提供包含原始值的结构化错误。
- 保持现有 phone role 与 action 行为。

**Non-Goals:**

- 不支持固话、分机、国际国家码号码或号码真实性查询。
- 不推断联系人角色，不自动修正缺失或错误数字。
- 不改变 OrderContext 当前的字符串字段类型。

## Decisions

### 只规范大陆手机号

采用 `^1[3-9]\\d{9}$` 作为归一化后的格式。允许 `+86` 和 `0086` 作为输入前缀，但内部去掉国家码，保持当前 `sender_phone`/`receiver_phone` 的兼容性。相比建立完整 E.164 对象，该方案更符合现阶段业务范围。

### 先清理再校验

归一化顺序为：去除首尾空白、空格、短横线和括号；识别并去除 `+86`/`0086`；最后进行严格格式校验。无法明确清理的字符直接报错，避免误删号码内容。

### 错误显式暴露

号码不合法时抛出结构化错误，包含实体类型、raw 值和失败原因。不会截断、补零或根据历史上下文猜测号码。

### 保留 raw/value 双字段

`attributes.value` 保存规范号码，`attributes.raw` 保存用户原文；这样 reducer 和下游接口使用 value，展示和审计使用 raw。

## Risks / Trade-offs

- [用户输入包含非标准标点] → 仅支持明确列出的分隔符，其余字符显式报错。
- [未来出现国际运输号码] → 保留 raw，并在未来单独扩展国际号码能力，不污染当前大陆号码契约。
- [extract 未输出 value] → normalizer 回退到 extraction_text，保证当前 extract 输出仍可用。
