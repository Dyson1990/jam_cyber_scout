"""plant_remind 业务流：检查到期浇水/施肥/调参 → feishu 发提醒 → 回写状态。"""

from dataclasses import dataclass

from appflow.item import Item

# 业务参数
FEISHU_CHAT_ID = "oc_e74a2ef5ba3da20b2d7cb72506e04451"
BITABLE_APP_TOKEN = "GS1UbFkgEadpuesRV8VcDnqOnxg"


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
    ("feishu", ["bitable", "load", BITABLE_APP_TOKEN], None),
    ("plant_keeper", ["remind", FEISHU_CHAT_ID], SendReq),
    ("feishu", [], SendResp),
    ("plant_keeper", ["apply"], None),
    ("feishu", ["bitable", "save", BITABLE_APP_TOKEN], None),
]
