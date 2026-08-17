import json
from datetime import datetime
from typing import Any, List, Mapping, Sequence

from ..infrastructure.llm import ChatMessage, LLMClient
from ..intent.resolver import StructuredIntentError
from .models import Entity

EXTRACTION_SYSTEM_PROMPT = """你是物流订单实体提取器。从用户的自然语言输入中提取与下单相关的实体信息，按实体在原文中出现的顺序依次提取；除 remark 外尽量使用原文短语，不要改写。remark 必须用概括性词语精炼表达，勿逐字复述长句。

输入第一行固定为「【参考时间】YYYY-MM-DD HH:MM（星期X）」，表示当前时间（系统时钟/中国时区），括号内为该日期对应的中文星期，用于辅助相对时间推理。所有相对时间表达均以该参考时间为基准换算为绝对时间。其后可能附带「【对话历史】」段，提供多轮上下文用于判断指代、省略与历史订单引用。

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

time —— 时间表达式
- context：history（历史订单引用）或 new_order（新需求）
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
- city：仅当用户明确提及城市名时输出，不带"市"后缀

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
- 支持的基础车型 code：
  four_wheel_small（四轮小件）、micro_van（微面）、small_van（小面）、
  medium_van（中面）、large_van（大面）、iveco（依维柯）、micro_truck（微货）、
  small_truck（小货）、medium_truck（中货）。
- 支持的标准车长 code：
  truck_3m8（3米8）、truck_4m2（4米2）、truck_5m2（5米2）、truck_6m2（6米2）、
  truck_6m8（6米8）、truck_7m6（7米6）、truck_8m2（8米2）、truck_8m6（8米6）、
  truck_9m6（9米6）、truck_11m7（11米7）、truck_12m5（12米5）、truck_13m（13米）、
  truck_13m7（13米7）、truck_15m（15米）、truck_16m（16米）、truck_17m5（17米5）。
- `attributes.value` 必须使用上述目录 code；`extraction_text` 保留用户在本轮使用的原文短语。
- 明确别名：小拉/轿车 → four_wheel_small；小面包 → small_van；面包车 → medium_van。
- 不要在此处推导微面/小面、中面/大面、微货/小货/中货之间的关系，也不要将“X米以上”选择为某个标准车长。

vehicle_specs —— 车辆能力、车厢类型、运输要求或装卸设备
- 支持的规格 code：cold_chain（冷链）、enclosed（厢式）、high_rail（高栏）、
  flatbed（平板）、dangerous_goods（危险品）、high_roof（高顶）、tail_lift（尾板）。
- 冷链、厢式、高栏、平板、危险品、高顶、尾板及其别名 MUST 输出为 `vehicle_specs`，不得输出为 `vehicle_type`。
- `attributes.value` 必须使用上述目录 code；`extraction_text` 保留用户原文短语。
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

order_id —— 订单号

语义规则：
- "从A到B"/"从A送到B"：A=装货地，B=卸货地
- "送到X"/"拉到X"：X=卸货地
- "到X装货"/"去X取货"：X=装货地
- "X收"/"X签收"：X=收货人
- "找X拿"/"X发货"：X=发货人
- 当用户引用历史订单时，相关实体 context 设为 history；新需求实体 context 设为 new_order

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
{"entities":[{"type":"cargo","action":"set","extraction_text":"两吨苹果","attributes":{"name":"苹果","weight":"2吨"}},{"type":"location","action":"set","extraction_text":"上海","attributes":{"role":"pickup","city":"上海"}},{"type":"location","action":"set","extraction_text":"温州","attributes":{"role":"dropoff","city":"温州"}}]}

示例3（remove）：
输入：【参考时间】2026-08-14 10:00（星期五）
用户：苹果不要了
输出：
{"entities":[{"type":"cargo","action":"remove","extraction_text":"苹果","attributes":{"name":"苹果"}}]}

示例4（replace）：
输入：【参考时间】2026-08-14 10:00（星期五）
用户：车型规格换成冷链车
输出：
{"entities":[{"type":"vehicle_specs","action":"replace","extraction_text":"冷链车","attributes":{"value":"cold_chain"}}]}

示例5（history context）：
输入：【参考时间】2026-08-14 10:00（星期五）
【对话历史】
user: 我要下单从上海运货到温州
assistant: 已为您创建草稿
用户：上次那个再发一单
输出：
{"entities":[{"type":"order_id","action":"set","extraction_text":"上次那个","attributes":{"context":"history"}}]}

示例6（cold-chain spec）：
输入：【参考时间】2026-08-14 10:00（星期五）
用户：要冷链车
输出：
{"entities":[{"type":"vehicle_specs","action":"set","extraction_text":"冷链车","attributes":{"value":"cold_chain"}}]}

示例7（combined vehicle and specs）：
输入：【参考时间】2026-08-14 10:00（星期五）
用户：要一辆4米2冷链厢式车
输出：
{"entities":[{"type":"vehicle_type","action":"set","extraction_text":"4米2","attributes":{"value":"truck_4m2"}},{"type":"vehicle_specs","action":"set","extraction_text":"冷链","attributes":{"value":"cold_chain"}},{"type":"vehicle_specs","action":"set","extraction_text":"厢式","attributes":{"value":"enclosed"}}]}

示例8（multiple specs independently）：
输入：【参考时间】2026-08-14 10:00（星期五）
用户：4米2高顶带尾板
输出：
{"entities":[{"type":"vehicle_type","action":"set","extraction_text":"4米2","attributes":{"value":"truck_4m2"}},{"type":"vehicle_specs","action":"set","extraction_text":"高顶","attributes":{"value":"high_roof"}},{"type":"vehicle_specs","action":"set","extraction_text":"带尾板","attributes":{"value":"tail_lift"}}]}

输出：仅返回符合以下 schema 的 JSON 对象：
{"entities":[{"type":"<实体类型>","action":"add"|"set"|"remove"|"replace","extraction_text":"<原文短语或概括>","attributes":{<类型特定属性>}}]}
- "type"、"action"、"extraction_text"、"attributes" 均为必填。
- 未识别到任何实体时返回 {"entities": []}。
不要包含任何其他键、文字或解释。
"""

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
        value = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise StructuredIntentError("LLM returned invalid extraction JSON") from exc
    if not isinstance(value, dict):
        raise StructuredIntentError("LLM extraction output must be a JSON object")
    return parse_entities(value)


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

    def extract(self, message: str, history: Sequence[Mapping[str, str]], reference_time: str) -> List[Entity]:
        user_message = _build_user_message(message, history, reference_time)
        response = self.client.chat([
            ChatMessage("system", EXTRACTION_SYSTEM_PROMPT),
            ChatMessage("user", user_message),
        ])
        return parse_entities_from_text(response.text)


def extract_entities(
    client: LLMClient,
    message: str,
    history: Sequence[Mapping[str, str]],
    reference_time: str,
) -> List[Entity]:
    """便利函数：提取带 action 的订单实体。"""
    return EntityExtractor(client).extract(message, history, reference_time)


__all__ = [
    "EXTRACTION_SYSTEM_PROMPT",
    "EntityExtractor",
    "extract_entities",
    "parse_entities",
    "parse_entities_from_text",
]
