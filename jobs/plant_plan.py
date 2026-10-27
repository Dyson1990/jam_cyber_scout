"""plant_plan 业务流：plant_keeper 出 prompt → deepseek 规划 → plant_keeper 回写计划。"""

from dataclasses import dataclass

from appflow.item import Item

# 业务参数
BITABLE_APP_TOKEN = "GS1UbFkgEadpuesRV8VcDnqOnxg"


@dataclass
class PlanReq(Item):
    """plant_keeper(plan) 输出，deepseek 输入。"""
    prompt: str


@dataclass
class PlanResp(Item):
    """deepseek 输出，plant_keeper(apply_plan) 输入。"""
    prompt: str
    reply: str = ""


STAGES = [
    ("feishu", ["bitable", "load", BITABLE_APP_TOKEN], None),
    ("plant_keeper", ["plan"], PlanReq),
    ("deepseek", [], PlanResp),
    ("plant_keeper", ["apply_plan"], None),
    ("feishu", ["bitable", "save", BITABLE_APP_TOKEN], None),
]
