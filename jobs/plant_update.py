"""plant_update 业务流：检查待确认植物/浇水器 → feishu 查表情 → 回写浇水/施肥时间。"""

from dataclasses import dataclass

from appflow.item import Item

# 业务参数
BITABLE_APP_TOKEN = "GS1UbFkgEadpuesRV8VcDnqOnxg"


@dataclass
class CheckReq(Item):
    """plant_keeper(check) 输出，feishu 输入。"""
    op: str      # "check"
    ref: str
    message_id: str


@dataclass
class CheckResp(Item):
    """feishu 输出，plant_keeper(apply) 输入。"""
    op: str      # "checked"
    ref: str
    reacted: bool
    action_time: int | None = None


STAGES = [
    ("feishu", ["bitable", "load", BITABLE_APP_TOKEN], None),
    ("plant_keeper", ["check"], CheckReq),
    ("feishu", [], CheckResp),
    ("plant_keeper", ["apply"], None),
    ("feishu", ["bitable", "save", BITABLE_APP_TOKEN], None),
]
