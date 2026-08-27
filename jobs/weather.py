"""weather 业务流：调 deepseek 查询未来 7 天天气。"""

from dataclasses import dataclass

from appflow.item import Item


@dataclass
class WeatherItem(Item):
    """deepseek 输出（原字段 + reply）。"""
    prompt: str
    reply: str = ""


STAGES = [
    ("deepseek", ["查询并总结未来 7 天（含今天）的天气情况，逐日列出日期/天气/温度/建议"], WeatherItem),
]
