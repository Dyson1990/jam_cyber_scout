"""生成浇水/施肥/调参提醒请求。"""

import json
import sys

from apps.plant_keeper import schedule, state


def _device_need_adjust(device: dict) -> bool:
    rec_i = device.get("recommended_interval_days")
    rec_d = device.get("recommended_water_duration")
    if rec_i is None and rec_d is None:
        return False
    if rec_i is not None and rec_i != device.get("interval_days"):
        return True
    if rec_d is not None and rec_d != device.get("water_duration"):
        return True
    return False


def remind() -> int:
    s = state.load()
    chat_id = s.get("feishu_chat_id", "")
    if not chat_id:
        print("缺少 feishu_chat_id 配置", file=sys.stderr)
        return 1

    device = s["device"]

    for plant in s["plants"]:
        if plant["remind_status"] != "idle":
            continue  # 待确认的等确认 job 处理，不重复提醒
        interval = plant.get("interval_days", 7)
        fert_interval = plant.get("fertilize_interval_days", 30)
        name = plant.get("name", plant["id"])

        water = (not plant.get("auto_water")) and schedule.water_due(plant, interval)
        fert = schedule.fertilize_due(plant, fert_interval)
        if not water and not fert:
            continue

        tasks = []
        if water:
            tasks.append("浇水")
        if fert:
            use = f"（{plant['fertilizer_use']}）" if plant.get("fertilizer_use") else ""
            tasks.append("施肥" + use)
        text = f"🌱 {name} 该{'、'.join(tasks)}啦，完成后在消息上点个 👍"
        if plant.get("care_note"):
            text += f"\n📋 {plant['care_note']}"
        print(json.dumps({
            "op": "send", "ref": plant["id"], "chat_id": chat_id, "text": text,
        }, ensure_ascii=False))
        sys.stdout.flush()

    if device.get("remind_status") == "idle" and _device_need_adjust(device):
        text = (
            f"💧 建议调整自动浇水器参数：间隔 {device['recommended_interval_days']} 天、"
            f"输水 {device['recommended_water_duration']} 秒"
            f"（当前 {device.get('interval_days')} 天 / {device.get('water_duration')} 秒），调好点 👍"
        )
        print(json.dumps({"op": "send", "ref": "device", "chat_id": chat_id, "text": text}, ensure_ascii=False))
        sys.stdout.flush()
    return 0
