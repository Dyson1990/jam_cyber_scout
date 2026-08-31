"""AI 规划养护计划 — 构建 prompt 交给 deepseek，解析回复回写状态。"""

import json
import re
import sys
from datetime import date

from apps.plant_keeper import state


def _plan_prompt() -> str:
    s = state.load()
    today = date.today()

    lines = [
        f"今天是 {today.isoformat()}。你是植物养护助手，请根据杭州 {today.month} 月的天气，为下列植物规划养护。",
        "要求：",
        "1. 浇水、施肥给到具体日期(YYYY-MM-DD)。",
        "2. 半水培植物按换水量(water_ml)估计吸收蒸发完的时间定下次换水日期。",
        "3. 判断是否需购买新肥料，buy_fertilizer 只列真正需新购的，与 care_note 施肥建议一致。",
        "4. 肥料用法：用哪几种肥料、取多少克/ml兑满容器、每盆施用量多少ml、怎么浇、是否需补浇水及补多少ml。",
        "5. care_note 只写养护技巧(通风/光照/修剪/防病)，不要写施肥或浇水判断；本次不施肥则 fertilizer_use 写「本次不施肥」，不要自相矛盾。",
        "6. 如需调整自动浇水器参数给建议。",
        "7. 施肥和浇水合并：施肥日兑水浇灌即算浇过水，next_water 必须晚于 next_fertilize，从施肥日起算一个周期（土培按 interval_days，半水培按换水量蒸发时间），不要与施肥日同日或更早。",
        "",
        "植物清单：",
    ]
    for p in s["plants"]:
        name = p.get("name", p["id"])
        loc = p.get("location", "未知")
        cult = p.get("cultivation", "土培")
        interval = p.get("interval_days", 7)
        how = "自动浇水器" if p.get("auto_water") else "手动浇水"
        line = f"- {p['id']} {name}，{loc}，{cult}，{how}，浇水间隔{interval}天"
        if p.get("water_ml"):
            line += f"，每次换水{p['water_ml']}ml"
        hist = p.get("fertilize_history") or []
        if hist:
            line += f"，最近施肥：{'、'.join(h[:10] for h in hist[-3:])}"
        lines.append(line)

    lines.append("")
    lines.append("现有肥料：")
    for f in s["fertilizers"]:
        label = f.get("name") or f.get("value")
        lines.append(f"- {f['id']} {label}")

    device = s["device"]
    lines.append("")
    lines.append(
        f"自动浇水器：间隔{device.get('interval_days')}天、每次输水{device.get('water_duration')}秒，"
        f"{device.get('valves')}个调节阀，200秒出水{device.get('ml_per_valve')}ml/个。"
    )
    lines.append("")
    mix = s.get("mix_container_ml", 1000)
    lines.append(f"配肥料容器：{mix}ml。取肥量直接给克/ml，不要给兑水比例。")
    lines.append("")
    lines.append("只输出 JSON，不要 markdown 代码块、不要解释文字，格式：")
    lines.append(
        '{"plants":[{"id":"g1","next_water":"YYYY-MM-DD","next_fertilize":"YYYY-MM-DD",'
        '"fertilizer_use":"肥料名+取X克/ml兑满容器+每盆施用量Yml+怎么浇+是否补浇水(补Zml)","care_note":"近期注意事项"}],'
        '"buy_fertilizer":["需新购的肥料名，无需则[]"],"device":{"interval_days":5,"water_duration":60}}'
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
            for k in ("next_water", "next_fertilize", "fertilizer_use", "care_note"):
                if p.get(k):
                    plant[k] = p[k]
            changed = True

        buy = result.get("buy_fertilizer")
        if isinstance(buy, list):
            s["buy_fertilizer"] = buy
            changed = True

        d = result.get("device")
        if isinstance(d, dict):
            for k in ("interval_days", "water_duration"):
                if d.get(k) is not None:
                    s["device"]["recommended_" + k] = d[k]
                    changed = True

    if changed:
        state.save(s)
    return 0
