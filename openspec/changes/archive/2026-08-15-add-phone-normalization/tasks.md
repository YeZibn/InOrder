## 1. Phone normalization

- [x] 1.1 创建手机号归一化模型和结构化错误
- [x] 1.2 实现空白、短横线、括号及 `+86`/`0086` 前缀清理
- [x] 1.3 实现大陆手机号格式校验并保留 raw/value
- [x] 1.4 将 phone entity 接入现有实体归一化接口

## 2. Reducer integration

- [x] 2.1 确保 sender/receiver role 下 set/replace 写入规范手机号
- [x] 2.2 确保 phone add 被拒绝，remove 行为保持不变
- [x] 2.3 保持非 phone entity 和输入上下文不受影响

## 3. Tests and compatibility

- [x] 3.1 覆盖标准号码、分隔符、`+86` 和 `0086` 输入
- [x] 3.2 覆盖非法长度、号段、字符及 raw/value 保留
- [x] 3.3 使用 conda agent 环境运行完整测试
