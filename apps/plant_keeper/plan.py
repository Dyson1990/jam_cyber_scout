"""AI 规划养护计划 — 构建 prompt 交给 deepseek，解析回复回写状态。"""

import json
import re
import sys
from datetime import date

from apps.plant_keeper import state


def _plan_prompt() -> str:
    s = state.load()
    today = date.today()
    cur_month = today.strftime("%Y-%m")

    lines = [
        f"今天是 {today.isoformat()}。你是植物养护助手，为杭州的下列植物规划本月养护。",
        "先分析再输出：",
        f"1) 结合杭州{today.month}月气候与每种植物品种习性，判断当前阶段（营养生长/孕蕾/开花/休眠）和氮磷钾需求；",
        "2) 对照「现有肥料」清单选肥：生长/开花期的植物都应施肥，休眠期或确实无需施肥的 next_fertilize 写 null；清单满足不了的列入 buy_fertilizer。",
        "",
        "输出要求：",
        "1. 日期用 YYYY-MM-DD；半水培按换水量(water_ml)估蒸发定下次换水日期。",
        "2. 施肥用兑水肥液，施肥当天即等于浇水（自动浇水器只自动浇水，施肥仍需手动）。手动且从未浇水的植物：next_water 写今天，要施肥则 next_fertilize 也写今天（一次完成）。",
        "3. 肥料用法写清：取多少克/ml兑满容器（同种肥料取肥量一致）、每盆多少ml、怎么浇。土培沿盆边浇、半水培倒储水盆、苔藓球均匀浸润。",
        "4. buy_fertilizer 只列清单里没有、且本次确实需要的肥料，别名算重复。",
        "5. care_note 写本月养护要点（光照/温度/通风/浇水/湿度/施肥时机/修剪/病虫害），80~150字，不写具体日期；本月已生成的写 null。",
        "6. fertilize_reason 写选肥依据，必须与 fertilizer_use 实际用肥一致；不施肥的 next_fertilize、fertilizer_use、fertilize_reason 都写 null。",
        "",
        "植物清单：",
    ]
    for p in s["plants"]:
        name = p.get("name", p["id"])
        loc = p.get("location", "未知")
        cult = p.get("cultivation", "土培")
        how = "自动浇水器" if p.get("auto_water") else "手动浇水"
        line = f"- {p['id']} {name}，{loc}，{cult}，{how}"
        if p.get("water_ml"):
            line += f"，每次换水{p['water_ml']}ml"
        if not p.get("auto_water"):
            lw = p.get("last_watered")
            line += f"，上次浇水{lw[:10]}" if lw else "，从未浇水"
        hist = p.get("fertilize_history") or []
        if hist:
            line += f"，最近施肥：{'、'.join(h[:10] for h in hist[-3:])}"
        else:
            line += "，从未施肥"
        cn = p.get("care_note")
        if isinstance(cn, list) and len(cn) == 2 and cn[0] == cur_month:
            line += "，care_note 本月已生成"
        lines.append(line)

    lines.append("")
    lines.append("现有肥料：")
    for f in s["fertilizers"]:
        label = f.get("name") or f.get("value")
        note = f.get("note")
        if note:
            lines.append(f"- {f['id']} {label}（{note}）")
        else:
            lines.append(f"- {f['id']} {label}")

    lines.append("")
    mix = s.get("mix_container_ml", 1000)
    lines.append(f"配肥料容器：{mix}ml。取肥量直接给克/ml，不要给兑水比例。")
    lines.append("")
    lines.append("只输出 JSON，不要 markdown 代码块、不要解释文字，格式：")
    lines.append(
        '{"plants":[{"id":"g1","next_water":"YYYY-MM-DD","next_fertilize":"YYYY-MM-DD",'
        '"fertilizer_use":"...","fertilize_reason":"...","care_note":"..."}],"buy_fertilizer":[]}'
    )
    return "\n".join(lines)


def plan() -> int:
    print(json.dumps({"prompt": _plan_prompt()}, ensure_ascii=False))
    sys.stdout.flush()
    return 0


def _extract_json(text: str):
    """从 AI 回复中提取 JSON 对象，容忍 markdown 代码块包裹。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def apply_plan() -> int:
    s = state.load()
    by_id = {p["id"]: p for p in s["plants"]}
    changed = False
    cur_month = date.today().strftime("%Y-%m")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        result = _extract_json(json.loads(line).get("reply", ""))
        if not result:
            print("[plant_keeper] 无法解析 AI 计划", file=sys.stderr)
            continue

        for p in result.get("plants", []):
            plant = by_id.get(p.get("id"))
            if not plant:
                continue
            if "next_water" in p:
                plant["next_water"] = p["next_water"]
            cn = p.get("care_note")
            if cn:
                plant["care_note"] = [cur_month, cn]
            # 施肥字段允许显式写 null，表示本次/近期不施肥
            for k in ("next_fertilize", "fertilizer_use", "fertilize_reason"):
                if k in p:
                    plant[k] = p[k]
            changed = True

        buy = result.get("buy_fertilizer")
        if isinstance(buy, list):
            s["buy_fertilizer"] = buy
            changed = True

    # 手动且从未浇水的植物：今天必须补水（施肥日期由 AI 决定，不在此覆盖）。
    today = date.today()
    for plant in s["plants"]:
        if not plant.get("auto_water") and not plant.get("last_watered"):
            plant["next_water"] = today.isoformat()
            changed = True

    if changed:
        state.save(s)
    return 0
