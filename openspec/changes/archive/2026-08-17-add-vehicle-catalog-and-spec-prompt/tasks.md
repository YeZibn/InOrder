## 1. Vehicle catalog

- [x] 1.1 创建 vehicle_type 静态目录，收录基础车型和标准车长 code、label、category、aliases、status
- [x] 1.2 创建 vehicle_specs 静态目录，收录冷链、厢式、高栏、平板、危险品、高顶、尾板及 group/aliases/status
- [x] 1.3 为目录增加读取接口和完整性测试，确保 code 唯一、别名可查、车长数据正确

## 2. Extract prompt correction

- [x] 2.1 修正 vehicle_type/vehicle_specs 的职责说明和冷链归类规则
- [x] 2.2 增加冷链、组合车型、多规格独立输出 few-shot 示例
- [x] 2.3 保留 extraction_text 原文并在示例 attributes 中使用目录 code
- [x] 2.4 按 prompt-changelog 约定记录 EXTRACTION_SYSTEM_PROMPT 变更

## 3. Tests and boundaries

- [x] 3.1 更新 prompt 内容断言，覆盖新增规格和冷链不属于 vehicle_type
- [x] 3.2 覆盖目录导出、规范 code 和边界范围
- [x] 3.3 使用 conda agent 环境运行完整测试，确认不改动 reducer 和模糊指代行为
