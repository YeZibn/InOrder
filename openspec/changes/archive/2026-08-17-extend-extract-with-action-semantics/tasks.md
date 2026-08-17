## 1. 模块与模型

- [x] 1.1 创建 `src/inorder_llm/extract/` 模块结构（`__init__.py` 导出公开 API）
- [x] 1.2 实现 `Entity` dataclass（`models.py`：`type`/`action`/`attributes`/`extraction_text`，`action` 为 `Literal["add","set","remove","replace"]`，含 `to_dict`）

## 2. Prompt

- [x] 2.1 编写 `EXTRACTION_SYSTEM_PROMPT`（`prompt.py`）：引入现成 14 类实体定义与全部语义归一规则（时间归一、车型归一、地址角色、人名拆分、history context 标记等）
- [x] 2.2 扩展 action 维度：action 枚举说明（add/set/remove/replace 语义）+ 判定规则（首次/无动作→set、加/再/多→add、不要了/删→remove、换/改成→replace）+ 每类 action 至少一个 few-shot 示例（输出含 action 字段）
- [x] 2.3 定义输出 JSON schema 说明（`{entities:[{type,action,extraction_text,attributes}]}`，严格 JSON 无多余文本）

## 3. Extractor 与解析

- [x] 3.1 实现 `parse_entities`（`parser.py`）：JSON → `List[Entity]`；校验 action 合法枚举、必要字段存在；失败抛 `StructuredIntentError`（含原始输出与解析错误）
- [x] 3.2 确认 `StructuredIntentError` 复用导入路径（位于 `intent/resolver.py`，extract 模块导入复用；如位置有出入则调整导入）
- [x] 3.3 实现 `EntityExtractor` 类（`extractor.py`，持 LLM client）+ `extract_entities(message, history, reference_time) -> List[Entity]` 纯函数
- [x] 3.4 实现消息构造：system=EXTRACTION_SYSTEM_PROMPT；user=参考时间行「【参考时间】YYYY-MM-DD HH:MM（星期X）」+ history 上下文段 + 用户本次输入；复用 `_json_call` 严格 JSON 模式

## 4. 测试与验证

- [x] 4.1 测试 action 四类提取（`test_extract.py`，mock LLM 返回）：add（"再加一吨苹果"）、set（"我要两吨苹果"）、remove（"苹果不要了"）、replace（"车型换成冷链车"）
- [x] 4.2 测试实体类型覆盖与归一：location 角色（从上海运到温州）、vehicle_type 归一（小面包→小面、面包车→中面）、cargo 属性、time context 标记
- [x] 4.3 测试解析健壮性：非法 JSON、非法 action 值、缺必要字段 → 均抛 `StructuredIntentError`
- [x] 4.4 测试输入参数：空 history 正常执行、有 history 时 context=history 标记、reference_time 注入 user message
- [x] 4.5 运行 `conda run -n agent python -m pytest -q` 全量通过 + `python -c "from inorder_llm.extract import extract_entities"` import smoke
- [x] 4.6 更新 `src/inorder_llm/PROMPT_CHANGELOG.md` 追加本次 extract prompt 变更记录（含评测结果：pytest 通过数 + 新增测试文件）
