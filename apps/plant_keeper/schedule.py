"""浇水/施肥到期判断 — remind 与 update 共用的纯函数。"""

from datetime import date


def water_due(plant: dict) -> bool:
    """浇水是否到期：AI 已排期则按 next_water；未排期且从未浇过则到期。"""
    if plant.get("next_water"):
        return date.today() >= date.fromisoformat(plant["next_water"])
    return not plant.get("last_watered")


def fertilize_due(plant: dict) -> bool:
    """施肥是否到期：仅按 AI 排期的 next_fertilize。"""
    nf = plant.get("next_fertilize")
    return bool(nf) and date.today() >= date.fromisoformat(nf)
