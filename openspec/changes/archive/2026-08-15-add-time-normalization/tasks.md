## 1. Time normalization model

- [x] 1.1 创建时间归一化结果模型和结构化错误，支持 raw、context、kind、start/end
- [x] 1.2 实现当前 extract 时间格式到 Asia/Shanghai ISO 格式的解析
- [x] 1.3 实现 start/end 非空、格式、顺序和单边开区间校验
- [x] 1.4 根据边界分类 fixed/range，并保持原始边界字段

## 2. Pipeline integration

- [x] 2.1 提供时间 Entity 和实体列表归一化接口，不修改输入对象
- [x] 2.2 将时间归一化接入 reducer，new_order 写入 delivery_time
- [x] 2.3 阻止 history 时间覆盖 delivery_time，并提供明确错误或分流结果

## 3. Tests and compatibility

- [x] 3.1 覆盖固定时间、闭区间、单边开区间和非法边界
- [x] 3.2 覆盖 context 校验、raw 保留、时区输出和输入不可变
- [x] 3.3 使用 conda agent 环境运行完整测试并验证既有 extract/reducer 行为
