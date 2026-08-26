"""植物浇水业务 App — 经 feishu App 收发消息，维护浇水状态。

阶段（用 args 区分，由 config.py 流水线串联）:
    remind  消息提醒：检查到期植物，输出 send 请求(JSONL)
    check   更新计划：检查待确认植物，输出 check 请求(JSONL)
    apply   读 feishu 结果，更新状态文件
"""

import json
import os
import sys
from datetime import datetime, timezone

from apps.plant_keeper import state

# Windows 控制台默认 GBK，强制 UTF-8 避免中文/emoji 输出报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def remind() -> int:
    chat_id = os.getenv("FEISHU_CHAT_ID", "")
    if not chat_id:
        print("缺少 FEISHU_CHAT_ID 环境变量", file=sys.stderr)
        return 1

    species = state.load("species.json")
    plans = state.load("plans.json")
    data = state.load("plants.json")
    now = datetime.now(timezone.utc)

    for plant in data["plants"]:
        if plant["remind_status"] != "idle":
            continue  # 待确认的等更新计划处理，不重复提醒
        plan = plans.get(plant["plan"], {})
        interval_days = plan.get("interval_days", 7)
        name = species.get(plant["species"], {}).get("name", plant["id"])

        if plant.get("last_watered"):
            last = datetime.fromisoformat(plant["last_watered"])
            due = (now - last).days >= interval_days
        else:
            due = True  # 从没浇过，首次立即提醒
        if due:
            print(json.dumps({
                "op": "send",
                "ref": plant["id"],
                "chat_id": chat_id,
                "text": f"🌱 {name} 该浇水啦（{interval_days} 天一次），浇完在消息上点个 👍",
            }, ensure_ascii=False))
        sys.stdout.flush()
    return 0


def check() -> int:
    data = state.load("plants.json")
    for plant in data["plants"]:
        if plant["remind_status"] == "waiting_confirm" and plant.get("pending_ref"):
            print(json.dumps({
                "op": "check",
                "ref": plant["id"],
                "message_id": plant["pending_ref"],
            }, ensure_ascii=False))
        sys.stdout.flush()
    return 0


def apply() -> int:
    data = state.load("plants.json")
    by_id = {p["id"]: p for p in data["plants"]}
    changed = False

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        res = json.loads(line)
        plant = by_id.get(res.get("ref"))
        if not plant:
            continue

        if res.get("op") == "sent":
            plant["remind_status"] = "waiting_confirm"
            plant["pending_ref"] = res.get("message_id")
            changed = True
        elif res.get("op") == "checked" and res.get("reacted"):
            plant["last_watered"] = datetime.fromtimestamp(
                res["action_time"] / 1000, tz=timezone.utc
            ).isoformat()
            plant["remind_status"] = "idle"
            plant["pending_ref"] = None
            changed = True

    if changed:
        state.save("plants.json", data)
    return 0


def main() -> int:
    if "remind" in sys.argv:
        return remind()
    if "check" in sys.argv:
        return check()
    if "apply" in sys.argv:
        return apply()
    print("用法: python -m apps.plant_keeper.entry [remind|check|apply]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
