"""确认浇水/施肥/调参并回写状态。"""

import json
import sys
from datetime import date, datetime, timedelta, timezone

from apps.plant_keeper import schedule, state


def check() -> int:
    s = state.load()
    for plant in s["plants"]:
        if plant["remind_status"] == "waiting_confirm" and plant.get("pending_ref"):
            print(json.dumps({
                "op": "check", "ref": plant["id"], "message_id": plant["pending_ref"],
            }, ensure_ascii=False))
            sys.stdout.flush()
    device = s["device"]
    if device.get("remind_status") == "waiting_confirm" and device.get("pending_ref"):
        print(json.dumps({
            "op": "check", "ref": "device", "message_id": device["pending_ref"],
        }, ensure_ascii=False))
        sys.stdout.flush()
    return 0


def apply() -> int:
    s = state.load()
    device = s["device"]
    by_id = {p["id"]: p for p in s["plants"]}
    changed = False
    now = datetime.now(timezone.utc)
    today = date.today()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        res = json.loads(line)
        ref = res.get("ref")

        if ref == "device":
            if res.get("op") == "sent":
                device["remind_status"] = "waiting_confirm"
                device["pending_ref"] = res.get("message_id")
                changed = True
            elif res.get("op") == "checked" and res.get("reacted"):
                if device.get("recommended_interval_days") is not None:
                    device["interval_days"] = device["recommended_interval_days"]
                if device.get("recommended_water_duration") is not None:
                    device["water_duration"] = device["recommended_water_duration"]
                device["recommended_interval_days"] = None
                device["recommended_water_duration"] = None
                device["remind_status"] = "idle"
                device["pending_ref"] = None
                changed = True
            continue

        plant = by_id.get(ref)
        if not plant:
            continue

        if res.get("op") == "sent":
            plant["remind_status"] = "waiting_confirm"
            plant["pending_ref"] = res.get("message_id")
            changed = True
        elif res.get("op") == "checked" and res.get("reacted"):
            interval = plant.get("interval_days", 7)
            fert_interval = plant.get("fertilize_interval_days", 30)
            if (not plant.get("auto_water")) and schedule.water_due(plant, interval):
                plant["last_watered"] = now.isoformat()
                plant["next_water"] = (today + timedelta(days=interval)).isoformat()
            if schedule.fertilize_due(plant, fert_interval):
                plant.setdefault("fertilize_history", []).append(now.isoformat())
                plant["next_fertilize"] = (today + timedelta(days=fert_interval)).isoformat()
            plant["remind_status"] = "idle"
            plant["pending_ref"] = None
            changed = True

    if changed:
        state.save(s)
    return 0
