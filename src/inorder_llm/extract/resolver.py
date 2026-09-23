import json
from datetime import datetime
from typing import Any, List, Mapping, Sequence

from ..infrastructure.llm import ChatMessage, LLMClient
from ..infrastructure.llm.text import strip_json_prefix
from ..infrastructure.llm.structured import call_with_format_repair, acall_with_format_repair
from ..intent.resolver import StructuredIntentError
from ..catalog import render_vehicle_prompt_vocabulary
from .models import Entity

LANGEXTRACT_ORDER_PROMPT_DESCRIPTION = f"""你是物流订单 grounded entity extractor。仅从【待提取文本】选择连续原文作为 extraction_text；【参考时间】仅用于相对时间计算，不能作为实体来源。每个实体 attributes 必须包含 action，且 action 只能是 add、set、remove、replace，由模型决定。不得猜测、补全或重写用户未表达的字段；未识别实体时返回空提取。

支持 time、location、person、phone、vehicle_type、vehicle_specs、cargo、follow_car_number、oneself_follow_flag、invoice_type、payment_type、service_type、remark。location 必须给 role=pickup/dropoff，并可包含用户明确表达的 province、city 与 full_address；province 和 city 均不得根据常识推断，full_address 必须来自待提取文本中的连续地址原文，不得补全或改写。time 给 start/end。车型和规格必须保留用户原文，不要生成或猜测 canonical code；remark 的 extraction_text 为用户原文，attributes.value 为简短业务概括。

{render_vehicle_prompt_vocabulary()}"""


def format_langextract_source(message: str, reference_time: str) -> str:
    return f"【参考时间】{reference_time}\n【待提取文本】{message}"


def build_langextract_order_examples():
    """Return schema-covering grounded examples for LangExtract."""
    from langextract.data import ExampleData, Extraction
    return [
        ExampleData("【参考时间】2026-08-17 10:00\n【待提取文本】两吨苹果从上海运到温州", [
            Extraction("cargo", "两吨苹果", attributes={"action": "set", "name": "苹果", "weight": "2吨", "quantity": None, "volume": None, "dimensions": None}),
            Extraction("location", "上海", attributes={"action": "set", "role": "pickup", "province": None, "city": "上海", "full_address": "上海"}),
            Extraction("location", "温州", attributes={"action": "set", "role": "dropoff", "province": None, "city": "温州", "full_address": "温州"}),
        ]),
        ExampleData("【参考时间】2026-08-17 10:00\n【待提取文本】设置一吨苹果，起运地温州，目的地上海。", [
            Extraction("cargo", "一吨苹果", attributes={"action": "set", "name": "苹果", "weight": "1吨", "quantity": None, "volume": None, "dimensions": None}),
            Extraction("location", "温州", attributes={"action": "set", "role": "pickup", "province": None, "city": "温州", "full_address": "温州"}),
            Extraction("location", "上海", attributes={"action": "set", "role": "dropoff", "province": None, "city": "上海", "full_address": "上海"}),
        ]),
        ExampleData("【参考时间】2026-08-17 10:00\n【待提取文本】从上海浦东金桥物流园3号仓库运到温州瓯海批发市场", [
            Extraction("location", "上海浦东金桥物流园3号仓库", attributes={"action": "set", "role": "pickup", "province": None, "city": "上海", "full_address": "上海浦东金桥物流园3号仓库"}),
            Extraction("location", "温州瓯海批发市场", attributes={"action": "set", "role": "dropoff", "province": None, "city": "温州", "full_address": "温州瓯海批发市场"}),
        ]),
        ExampleData("【参考时间】2026-08-17 10:00\n【待提取文本】再加一吨苹果，4米2冷链厢式车", [
            Extraction("cargo", "一吨苹果", attributes={"action": "add", "name": "苹果", "weight": "1吨", "quantity": None, "volume": None, "dimensions": None}),
            Extraction("vehicle_type", "4米2", attributes={"action": "set", "value": "4米2"}),
            Extraction("vehicle_specs", "冷链", attributes={"action": "set", "value": "冷链"}),
            Extraction("vehicle_specs", "厢式", attributes={"action": "set", "value": "厢式"}),
        ]),
        ExampleData("【参考时间】2026-08-17 10:00\n【待提取文本】明天上午王强收，电话13800138000，苹果容易碎轻拿轻放", [
            Extraction("time", "明天上午", attributes={"action": "set", "start": "2026-08-18 06:00", "end": "2026-08-18 12:00"}),
            Extraction("person", "王强", attributes={"action": "set", "role": "receiver", "surname": "王", "name": "强"}),
            Extraction("phone", "13800138000", attributes={"action": "set", "role": "receiver", "value": "13800138000"}),
            Extraction("remark", "苹果容易碎轻拿轻放", attributes={"action": "set", "value": "易碎轻放"}),
        ]),
        ExampleData("【参考时间】2026-08-17 10:00\n【待提取文本】两人跟车，我跟车，到付不开票，快车，订单A123", [
            Extraction("follow_car_number", "两人跟车", attributes={"action": "set", "value": 2}),
            Extraction("oneself_follow_flag", "我跟车", attributes={"action": "set", "value": 1}),
            Extraction("payment_type", "到付", attributes={"action": "set", "value": 0}),
            Extraction("invoice_type", "不开票", attributes={"action": "set", "value": 1}),
            Extraction("service_type", "快车", attributes={"action": "set", "value": "express"}),
        ]),
        ExampleData("【参考时间】2026-08-17 10:00\n【待提取文本】小车，9米以上", [
            Extraction("vehicle_type", "小车", attributes={"action": "set", "value": "小车"}),
            Extraction("vehicle_type", "9米以上", attributes={"action": "set", "value": "9米以上"}),
        ]),
    ]

EXTRACTION_SYSTEM_PROMPT = """你是物流订单实体提取器。从用户的自然语言输入中提取与下单相关的实体信息，按实体在原文中出现的顺序依次提取；除 remark 外尽量使用原文短语，不要改写。remark 必须用概括性词语精炼表达，勿逐字复述长句。

输入第一行固定为「【参考时间】YYYY-MM-DD HH:MM（星期X）」，表示当前时间（系统时钟/中国时区），括号内为该日期对应的中文星期，用于辅助相对时间推理。所有相对时间表达均以该参考时间为基准换算为绝对时间。其后可能附带「【对话历史】」段，提供当前会话上下文用于判断指代与省略；不得将其解释为历史订单数据。

每个提取出的实体 MUST 携带 action 字段，表示本轮对该实体应用的操作。action 取值：
- add：增量累加（如"再加一吨苹果"——在已有基础上增加）
- set：覆盖设置/首次声明（如"我要两吨苹果"——设置或覆盖该字段值）
- remove：删除/移除（如"苹果不要了"——移除该实体）
- replace：替换/换成（如"车型换成冷链车"——替换为另一个值，多用于单值字段如车型、地址）

action 判定规则：
- 首次出现且无明确动作动词 → set
- 携带"加/再/多/补充"等增量信号 → add
- 携带"不要了/删/取消/去掉"等移除信号 → remove
- 携带"换/改成/换成/改为"等替换信号 → replace
- 单值字段（车型、地址、支付方式等）的修改通常为 replace；可累加字段（货物数量）的增量为 add

实体类型说明：

time —— 当前订单送达时间表达式
- start：时间区间开始，绝对时间「YYYY-MM-DD HH:MM」
- end：时间区间结束，绝对时间「YYYY-MM-DD HH:MM」

时间语义归一规则：
1. 具体时刻：start 与 end 相同
2. 时段表达：start/end 为该时段起止
   - 上午：06:00-12:00
   - 下午：12:00-18:00
   - 晚上：18:00-23:59
3. 整日：start=当日 00:00，end=当日 23:59
4. 整月：start=该月1日 00:00，end=该月最后一天 23:59
5. 开区间「X前」：start 为空，end=参考时间往前推X
6. 开区间「X后」：start=参考时间往后推X，end 为空
7. 闭区间「过去X里」：start=参考时间往前推X，end=参考时间
8. 闭区间「未来X里」：start=参考时间，end=参考时间往后推X

location —— 地址
- role：pickup（装货地）或 dropoff（卸货地）
- province：仅当用户明确提及省/自治区/直辖市名称时输出，去除“省”等后缀；未出现时必须为 null，不得根据 city 推断
- city：仅当用户明确提及城市名时输出，不带"市"后缀；无法确定时不要猜测
- full_address：用户本轮明确表达的完整地址连续原文，至少保留城市表达；只有城市时与城市表达相同。不得从上下文补全、拆分、标准化或改写地址

person —— 人名/称呼
- role：sender（发货人）或 receiver（收货人）
- 拆分为 surname（姓）和 name（名）
- 示例：
  - "老王" → surname="王"，name=""
  - "欧阳夏丹" → surname="欧阳"，name="夏丹"

phone —— 手机号
- role：sender 或 receiver

vehicle_type —— 基础车型或标准车长
- 只提取基础车型和标准车长，不提取车辆能力、车厢类型、运输要求或装卸设备。
- 车型词汇以本提示中的 catalog 词汇为参考；`extraction_text` 必须保留用户本轮使用的连续原文短语。
- 不要求、不得猜测或强制生成 canonical code；`attributes.value` 如需输出也必须保留用户原文表达。
- 不要把“小车”“X米左右”“X米以上”“之前那个车”等模糊、范围或指代表达选择成某个具体车型。

vehicle_specs —— 车辆能力、车厢类型、运输要求或装卸设备
- 冷链、厢式、高栏、平板、危险品、高顶、尾板及其别名 MUST 输出为 `vehicle_specs`，不得输出为 `vehicle_type`。
- `extraction_text` 必须保留用户原文短语；不要求、不得猜测或强制生成 canonical code。
- 同一句中的多个规格必须各输出一个独立的 `vehicle_specs` entity，不要拼成一个值。

cargo —— 货物信息
属性可包含：
- name
- weight
- dimensions
- volume
- quantity

follow_car_number —— 跟车人数
- attributes.value 为整数
- 仅表达跟车意图但未明确人数时，默认为 1

oneself_follow_flag —— 是否本人跟车
- 1：本人跟车
- 2：非本人跟车

invoice_type —— 开票类型
- 1：不开票或电子普票
- 2：纸质专票

payment_type —— 支付方式
- 0：到付
- 1：预付

service_type —— 品类/服务类型
枚举值：快车、特快、用户出价、拼车

remark —— 备注
- extraction_text 必须为概括性短语，例如：
  - "装货地电联"
  - "易碎轻放"
- 多项备注用分号拼接

语义规则：
- "从A到B"/"从A送到B"：A=装货地，B=卸货地
- "送到X"/"拉到X"：X=卸货地
- "到X装货"/"去X取货"：X=装货地
- "X收"/"X签收"：X=收货人
- "找X拿"/"X发货"：X=发货人

Few-shot 示例：

示例1（add）：
输入：【参考时间】2026-08-14 10:00（星期五）
用户：再加一吨苹果
输出：
{"entities":[{"type":"cargo","action":"add","extraction_text":"一吨苹果","attributes":{"name":"苹果","weight":"1吨"}}]}

示例2（set）：
输入：【参考时间】2026-08-14 10:00（星期五）
用户：我要两吨苹果从上海运到温州
输出：
{"entities":[{"type":"cargo","action":"set","extraction_text":"两吨苹果","attributes":{"name":"苹果","weight":"2吨"}},{"type":"location","action":"set","extraction_text":"上海","attributes":{"role":"pickup","city":"上海","full_address":"上海"}},{"type":"location","action":"set","extraction_text":"温州","attributes":{"role":"dropoff","city":"温州","full_address":"温州"}}]}

示例2a（详细地址）：
输入：【参考时间】2026-08-14 10:00（星期五）
用户：从上海市浦东新区金桥镇某物流园A区3号仓库送到浙江省温州市瓯海区某批发市场
输出：
{"entities":[{"type":"location","action":"set","extraction_text":"上海市浦东新区金桥镇某物流园A区3号仓库","attributes":{"role":"pickup","province":"上海","city":"上海","full_address":"上海市浦东新区金桥镇某物流园A区3号仓库"}},{"type":"location","action":"set","extraction_text":"浙江省温州市瓯海区某批发市场","attributes":{"role":"dropoff","province":"浙江","city":"温州","full_address":"浙江省温州市瓯海区某批发市场"}}]}

示例3（remove）：
输入：【参考时间】2026-08-14 10:00（星期五）
用户：苹果不要了
输出：
{"entities":[{"type":"cargo","action":"remove","extraction_text":"苹果","attributes":{"name":"苹果"}}]}

示例4（replace）：
输入：【参考时间】2026-08-14 10:00（星期五）
用户：车型规格换成冷链车
输出：
{"entities":[{"type":"vehicle_specs","action":"replace","extraction_text":"冷链车","attributes":{"value":"冷链车"}}]}

示例5（cold-chain spec）：
输入：【参考时间】2026-08-14 10:00（星期五）
用户：要冷链车
输出：
{"entities":[{"type":"vehicle_specs","action":"set","extraction_text":"冷链车","attributes":{"value":"冷链车"}}]}

示例6（combined vehicle and specs）：
输入：【参考时间】2026-08-14 10:00（星期五）
用户：要一辆4米2冷链厢式车
输出：
{"entities":[{"type":"vehicle_type","action":"set","extraction_text":"4米2","attributes":{"value":"4米2"}},{"type":"vehicle_specs","action":"set","extraction_text":"冷链","attributes":{"value":"冷链"}},{"type":"vehicle_specs","action":"set","extraction_text":"厢式","attributes":{"value":"厢式"}}]}

示例7（multiple specs independently）：
输入：【参考时间】2026-08-14 10:00（星期五）
用户：4米2高顶带尾板
输出：
{"entities":[{"type":"vehicle_type","action":"set","extraction_text":"4米2","attributes":{"value":"4米2"}},{"type":"vehicle_specs","action":"set","extraction_text":"高顶","attributes":{"value":"高顶"}},{"type":"vehicle_specs","action":"set","extraction_text":"带尾板","attributes":{"value":"带尾板"}}]}

输出：仅返回符合以下 schema 的 JSON 对象：
{"entities":[{"type":"<实体类型>","action":"add"|"set"|"remove"|"replace","extraction_text":"<原文短语或概括>","attributes":{<类型特定属性>}}]}
- "type"、"action"、"extraction_text"、"attributes" 均为必填。
- 未识别到任何实体时返回 {"entities": []}。
不要包含任何其他键、文字或解释。
""" + "\n车型 catalog 词汇（仅用于识别和分类，车型字段必须保留用户原文，不得输出 canonical code）：\n" + render_vehicle_prompt_vocabulary()

_VALID_ACTIONS = ("add", "set", "remove", "replace")
_REQUIRED_FIELDS = ("type", "action", "extraction_text", "attributes")
_WEEKDAY_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def parse_entities(value: Mapping[str, Any]) -> List[Entity]:
    """将解析后的 JSON 对象转为 Entity 列表。校验 action 合法枚举与必要字段。"""
    items = value.get("entities")
    if not isinstance(items, list):
        raise StructuredIntentError("entities must be an array")

    entities: List[Entity] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise StructuredIntentError(f"entity[{idx}] must be an object")
        for field_name in _REQUIRED_FIELDS:
            if field_name not in item:
                raise StructuredIntentError(f"entity[{idx}] missing field: {field_name}")

        action = item["action"]
        if action not in _VALID_ACTIONS:
            raise StructuredIntentError(
                f"entity[{idx}] invalid action '{action}'; expected one of {_VALID_ACTIONS}"
            )

        attributes = item["attributes"]
        if not isinstance(attributes, dict):
            raise StructuredIntentError(f"entity[{idx}] attributes must be an object")

        entities.append(
            Entity(
                type=item["type"],
                action=action,  # type: ignore[arg-type]
                attributes=attributes,
                extraction_text=item["extraction_text"],
            )
        )
    return entities


def parse_entities_from_text(text: str) -> List[Entity]:
    """将 LLM 返回的原始文本解析为 Entity 列表。"""
    try:
        value = json.loads(strip_json_prefix(text))
    except (TypeError, ValueError) as exc:
        raise StructuredIntentError("LLM returned invalid extraction JSON") from exc
    if not isinstance(value, dict):
        raise StructuredIntentError("LLM extraction output must be a JSON object")
    return parse_entities(value)


def _validate_location_attributes(entities: Sequence[Entity], source_text: str) -> None:
    """Validate address fields without normalizing or inferring their meaning."""
    for index, entity in enumerate(entities):
        if entity.type != "location":
            continue
        attrs = entity.attributes
        role = attrs.get("role")
        if role not in ("pickup", "dropoff"):
            raise StructuredIntentError(
                f"entity[{index}] location role must be pickup or dropoff"
            )
        city = attrs.get("city")
        if city is not None and (not isinstance(city, str) or not city.strip()):
            raise StructuredIntentError(f"entity[{index}] location city must be a non-empty string or null")
        province = attrs.get("province")
        if province is not None and (not isinstance(province, str) or not province.strip()):
            raise StructuredIntentError(f"entity[{index}] location province must be a non-empty string or null")
        full_address = attrs.get("full_address")
        if full_address is not None:
            if not isinstance(full_address, str) or not full_address.strip():
                raise StructuredIntentError(
                    f"entity[{index}] location full_address must be a non-empty string or null"
                )
            if full_address not in source_text:
                raise StructuredIntentError(
                    f"entity[{index}] location full_address must come from the extraction source"
                )


def _format_reference_time(reference_time: str) -> str:
    dt = datetime.strptime(reference_time, "%Y-%m-%d %H:%M")
    return f"【参考时间】{reference_time}（{_WEEKDAY_CN[dt.weekday()]}）"


def _format_history(history: Sequence[Mapping[str, str]]) -> str:
    if not history:
        return ""
    lines = ["【对话历史】"]
    for msg in history:
        lines.append(f"{msg.get('role', '')}: {msg.get('content', '')}")
    return "\n".join(lines)


def _build_user_message(message: str, history: Sequence[Mapping[str, str]], reference_time: str) -> str:
    parts = [_format_reference_time(reference_time)]
    hist = _format_history(history)
    if hist:
        parts.append(hist)
    parts.append(message)
    return "\n".join(parts)


class EntityExtractor:
    """订单实体提取器，持 LLM client，输出带 action 的 Entity 列表。"""

    def __init__(self, client: LLMClient):
        self.client = client

    def extract(self, message: str, history_or_reference, reference_time: str = None) -> List[Entity]:
        reference_time = reference_time or history_or_reference
        user_message = _build_user_message(message, [], reference_time)
        messages = [
            ChatMessage("system", EXTRACTION_SYSTEM_PROMPT),
            ChatMessage("user", user_message),
        ]
        entities = call_with_format_repair(self.client, messages, parse_entities_from_text, "上一次输出无法解析。请严格只返回符合要求的 entities JSON 对象，不要添加解释或 Markdown。")
        _validate_location_attributes(entities, message)
        return entities

    async def aextract(self, message: str, history_or_reference, reference_time: str = None, deadline_at: float = None) -> List[Entity]:
        anchor = reference_time or history_or_reference
        messages = [ChatMessage("system", EXTRACTION_SYSTEM_PROMPT), ChatMessage("user", _build_user_message(message, [], anchor))]
        entities = await acall_with_format_repair(self.client, messages, parse_entities_from_text, "上一次输出无法解析。请严格只返回符合要求的 entities JSON 对象，不要添加解释或 Markdown。", deadline_at)
        _validate_location_attributes(entities, message)
        return entities


def extract_entities(
    client: LLMClient,
    message: str,
    history_or_reference,
    reference_time: str = None,
) -> List[Entity]:
    """便利函数：提取带 action 的订单实体。"""
    return EntityExtractor(client).extract(message, history_or_reference, reference_time)


__all__ = [
    "EXTRACTION_SYSTEM_PROMPT",
    "LANGEXTRACT_ORDER_PROMPT_DESCRIPTION",
    "build_langextract_order_examples",
    "format_langextract_source",
    "EntityExtractor",
    "extract_entities",
    "parse_entities",
    "parse_entities_from_text",
]
