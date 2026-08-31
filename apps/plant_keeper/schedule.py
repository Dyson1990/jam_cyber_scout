"""浇水/施肥到期判断 — remind 与 update 共用的纯函数。"""

from datetime import date, datetime, timezone


def water_due(plant: dict, interval_days: int) -> bool:
    """浇水是否到期：next_water 优先，其次 last_watered+间隔，从未浇过则到期。"""
    if plant.get("next_water"):
        return date.today() >= date.fromisoformat(plant["next_water"])
    if plant.get("last_watered"):
        last = datetime.fromisoformat(plant["last_watered"])
        return (datetime.now(timezone.utc) - last).days >= interval_days
    return True


def fertilize_due(plant: dict, interval_days: int) -> bool:
    """施肥是否到期：next_fertilize 优先，其次 last_fertilized+间隔，无记录则等 AI 排期。"""
    if plant.get("next_fertilize"):
        return date.today() >= date.fromisoformat(plant["next_fertilize"])
    hist = plant.get("fertilize_history")
    if hist:
        last = datetime.fromisoformat(hist[-1])
        return (datetime.now(timezone.utc) - last).days >= interval_days
    return False
