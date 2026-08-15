## 1. Normalization model and mappings

- [x] 1.1 创建独立 normalization 模块与归一化结果/错误模型，支持保留 raw 与规范值
- [x] 1.2 定义 payment_type、invoice_type、oneself_follow_flag 和 service_type 的集中映射表及别名
- [x] 1.3 实现四类枚举的幂等归一化，接受中文表达、整数值和 service code
- [x] 1.4 对未知或类型错误的枚举返回包含实体类型、原始值和支持范围的结构化错误

## 2. Pipeline integration

- [x] 2.1 提供对 Entity 或实体列表的归一化接口，不修改输入对象或 OrderContext
- [x] 2.2 将归一化实体接入现有 reducer 调用边界，确保 reducer 接收稳定内部值
- [x] 2.3 明确并覆盖未纳入本次范围的车型、跟车人数、度量单位和货物属性推断行为

## 3. Tests and compatibility

- [x] 3.1 为四类枚举的标准表达、别名和已归一化值补充单元测试
- [x] 3.2 为幂等性、未知值、输入不可变和 raw 保留补充测试
- [x] 3.3 使用 conda agent 环境运行完整测试并修复兼容性问题
