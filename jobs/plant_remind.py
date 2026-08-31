"""plant_remind 业务流：检查到期浇水/施肥/调参 → feishu 发提醒 → 回写状态。"""

from dataclasses import dataclass

from appflow.item import Item


@dataclass
class SendReq(Item):
    """plant_keeper(remind) 输出，feishu 输入。"""
    op: str      # "send"
    ref: str
    chat_id: str
    text: str


@dataclass
class SendResp(Item):
    """feishu 输出，plant_keeper(apply) 输入。"""
    op: str      # "sent"
    ref: str
    message_id: str


STAGES = [
    ("plant_keeper", ["remind"], SendReq),
    ("feishu", [], SendResp),
    ("plant_keeper", ["apply"], None),
]
