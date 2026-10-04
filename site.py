"""生成 GitHub Pages 站点：扫描 .github/workflows 里激活的 job，产出静态 index.html。

激活 = 出现在某个 workflow 的 `python main.py <job>` 调用里。
"""
import ast
import datetime as _dt
import re
from pathlib import Path

ROOT = Path(__file__).parent
WF_DIR = ROOT / ".github" / "workflows"
OUT_DIR = ROOT / "site"
OUT = OUT_DIR / "index.html"

DOW_CN = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]


def _cron_to_text(cron: str) -> str:
    """cron → 中文可读（转北京时间 UTC+8）。"""
    parts = cron.split()
    if len(parts) != 5:
        return cron
    mi, hr, dom, _mon, dow = parts
    try:
        hours = [int(x) for x in hr.split(",")]
    except ValueError:
        return cron

    roll = 0
    labels = []
    for h in hours:
        t = h + 8
        roll = max(roll, t // 24)
        mm = "00" if mi == "*" else f"{int(mi):02d}"
        labels.append(f"{t % 24:02d}:{mm}")

    if dow == "*" and dom == "*":
        day = "每天"
    elif dom != "*":
        day = f"每月 {dom} 日"
    else:
        try:
            days = [int(x) % 7 for x in dow.split(",")]
        except ValueError:
            return cron
        if roll:
            days = [(d + roll) % 7 for d in days]
        day = " · ".join(f"每{DOW_CN[d]}" for d in days)

    return f"{day} {' / '.join(labels)}"


def _workflows() -> list[dict]:
    out = []
    for wf in sorted(WF_DIR.glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        jobs = re.findall(r"python\s+main\.py\s+(\w+)", text)
        if not jobs:
            continue  # 无业务 job 的 workflow（如 site.yml 自身）不展示
        name = re.search(r"^name:\s*(.+)$", text, re.M)
        crons = re.findall(r"cron:\s*[\"']?([^\"'\s][^\"'\n]*)", text)
        triggers = []
        if crons:
            triggers.append("定时")
        if re.search(r"workflow_dispatch", text):
            triggers.append("手动")
        if re.search(r"^\s*push\s*:", text, re.M):
            triggers.append("推送")
        out.append({
            "name": name.group(1).strip() if name else wf.stem,
            "cron": _cron_to_text(crons[0]) if crons else "—",
            "jobs": jobs,
            "triggers": triggers,
        })
    return out


def _app_counts() -> dict[str, int]:
    """统计每个 app 被 jobs 的 STAGES 引用的次数。"""
    counts: dict[str, int] = {}
    for jf in sorted((ROOT / "jobs").glob("*.py")):
        if jf.name.startswith("_"):
            continue
        try:
            tree = ast.parse(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for t in node.targets:
                if not (isinstance(t, ast.Name) and t.id == "STAGES"):
                    continue
                stages = node.value
                if not isinstance(stages, (ast.List, ast.Tuple)):
                    continue
                for elt in stages.elts:
                    if isinstance(elt, (ast.Tuple, ast.List)) and elt.elts:
                        first = elt.elts[0]
                        if isinstance(first, ast.Constant) and isinstance(first.value, str):
                            counts[first.value] = counts.get(first.value, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def _render(ws: list[dict]) -> str:
    n_jobs = sum(len(w["jobs"]) for w in ws)
    n_cron = sum(1 for w in ws if w["cron"] != "—")

    cards = []
    for w in ws:
        chips = "".join(f'<span class="chip">{j}</span>' for j in w["jobs"])
        tags = "".join(f'<span class="tag">{t}</span>' for t in w["triggers"])
        cards.append(
            f'<article class="card"><div class="card-top">'
            f'<h3>{w["name"]}</h3><span class="badge">活跃</span></div>'
            f'<div class="cron">🕐 {w["cron"]}</div>'
            f'<div class="chips">{chips}</div>'
            f'<div class="tags">{tags}</div></article>'
        )
    body = "\n".join(cards) if cards else '<p class="empty">暂无激活的 job</p>'

    counts = _app_counts()
    max_c = max(counts.values()) if counts else 1
    bars = "".join(
        f'<div class="bar-row"><span class="bar-label">{name}</span>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{c / max_c * 100:.1f}%"></div></div>'
        f'<span class="bar-val">{c}</span></div>'
        for name, c in counts.items()
    )

    stats = [
        ("激活 Job", n_jobs),
        ("定时任务", n_cron),
        ("工作流", len(ws)),
        ("数据源", n_jobs),
    ]
    stat_html = "".join(
        f'<div class="stat"><div class="num">{v}</div><div class="label">{k}</div></div>'
        for k, v in stats
    )

    updated = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cyber Scout · 智能调度看板</title>
<style>
:root {{
  --bg:#080b12; --panel:#101522; --panel2:#161d2e; --line:#232c42;
  --fg:#e8ecf5; --muted:#8b94a8; --accent:#4ff0c8; --accent2:#38bdf8;
}}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:var(--bg); color:var(--fg); font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; line-height:1.6; }}
a {{ color:inherit; text-decoration:none; }}

/* 顶部导航 */
nav {{ position:sticky; top:0; z-index:10; display:flex; align-items:center; justify-content:space-between;
  padding:14px 28px; background:rgba(8,11,18,.85); backdrop-filter:blur(10px); border-bottom:1px solid var(--line); }}
.brand {{ display:flex; align-items:center; gap:10px; font-weight:700; font-size:16px; }}
.logo {{ width:26px; height:26px; border-radius:7px; background:linear-gradient(135deg,var(--accent),var(--accent2)); }}
.nav-links {{ display:flex; gap:22px; color:var(--muted); font-size:13px; }}
.status-pill {{ display:flex; align-items:center; gap:7px; font-size:12px; color:var(--accent);
  border:1px solid var(--accent); padding:5px 12px; border-radius:999px; }}
.dot {{ width:7px; height:7px; border-radius:50%; background:var(--accent); box-shadow:0 0 8px var(--accent); }}

/* Hero */
.hero {{ padding:64px 28px 40px; text-align:center; }}
.eyebrow {{ color:var(--accent); font-size:12px; letter-spacing:3px; text-transform:uppercase; margin-bottom:14px; }}
h1 {{ font-size:44px; font-weight:800; background:linear-gradient(120deg,#fff,var(--accent),var(--accent2));
  -webkit-background-clip:text; background-clip:text; color:transparent; }}
.hero p {{ color:var(--muted); font-size:16px; margin-top:14px; max-width:560px; margin-inline:auto; }}

/* 统计 */
.stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; max-width:960px; margin:36px auto 0; padding:0 20px; }}
.stat {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:24px; text-align:center; }}
.num {{ font-size:36px; font-weight:800; color:var(--accent); }}
.label {{ color:var(--muted); font-size:13px; margin-top:6px; }}

/* 卡片区 */
main {{ max-width:960px; margin:0 auto; padding:56px 20px 64px; }}
.sec-head {{ display:flex; align-items:baseline; justify-content:space-between; margin-bottom:22px; }}
.sec-head h2 {{ font-size:22px; }}
.sec-head .hint {{ color:var(--muted); font-size:12px; }}
.grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:18px; }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:22px;
  transition:transform .15s, border-color .15s; }}
.card:hover {{ transform:translateY(-3px); border-color:var(--accent); }}
.card-top {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; }}
.card h3 {{ font-size:17px; }}
.badge {{ font-size:11px; color:var(--accent); border:1px solid var(--accent); border-radius:999px; padding:3px 10px; }}
.cron {{ color:var(--fg); font-size:14px; margin-bottom:14px; }}
.chips {{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:14px; }}
.chip {{ color:var(--accent2); border:1px solid var(--accent2); border-radius:999px; padding:4px 12px; font-size:13px; }}
.tags {{ display:flex; gap:8px; }}
.tag {{ color:var(--muted); background:var(--panel2); border-radius:6px; padding:3px 10px; font-size:11px; }}
.empty {{ color:var(--muted); }}

/* 条形图 */
.chart {{ background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:24px; margin-top:18px; }}
.bar-row {{ display:grid; grid-template-columns:130px 1fr 32px; align-items:center; gap:14px; margin:12px 0; }}
.bar-label {{ font-size:13px; color:var(--fg); text-align:right; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.bar-track {{ background:var(--panel2); border-radius:999px; height:20px; overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:999px; background:linear-gradient(90deg,var(--accent),var(--accent2)); }}
.bar-val {{ font-size:12px; color:var(--muted); text-align:right; }}

/* 页脚 */
footer {{ border-top:1px solid var(--line); padding:28px; text-align:center; color:var(--muted); font-size:12px; }}
footer span {{ margin:0 10px; }}
@media (max-width:640px) {{ .stats,.grid {{ grid-template-columns:1fr; }} h1 {{ font-size:32px; }} }}
</style>
</head>
<body>
<nav>
  <div class="brand"><span class="logo"></span>Cyber Scout</div>
  <div class="nav-links"><a href="#jobs">工作流</a><a href="#stats">概览</a></div>
  <div class="status-pill"><span class="dot"></span>系统运行中</div>
</nav>

<header class="hero">
  <div class="eyebrow">Intelligent Scheduling</div>
  <h1>Cyber Scout 调度看板</h1>
  <p>实时展示当前已激活的自动化工作流与定时任务，所有业务 Job 一览无余。</p>
</header>

<section class="stats" id="stats">
  {stat_html}
</section>

<main id="jobs">
  <div class="sec-head">
    <h2>激活的工作流</h2>
    <span class="hint">时间均为北京时间（UTC+8）</span>
  </div>
  <div class="grid">{body}</div>

  <div class="sec-head" style="margin-top:48px">
    <h2>App 引用次数</h2>
    <span class="hint">每个 App 被各 job 的 STAGES 引用的次数</span>
  </div>
  <div class="chart">{bars}</div>
</main>

<footer>
  <span>© Cyber Scout</span><span>更新于 {updated}</span><span>Powered by GitHub Actions</span>
</footer>
</body></html>"""


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    OUT.write_text(_render(_workflows()), encoding="utf-8")


if __name__ == "__main__":
    main()
