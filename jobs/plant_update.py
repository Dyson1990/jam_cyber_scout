"""plant_update 业务流：检查待确认植物 → feishu 查表情 → 回写浇水时间。"""

from dataclasses import dataclass

from appflow.item import Item


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
    ("plant_keeper", ["check"], CheckReq),
    ("feishu", [], CheckResp),
    ("plant_keeper", ["apply"], None),
]
