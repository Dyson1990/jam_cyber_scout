"""生成 GitHub Pages 站点：扫描 .github/workflows 里激活的 job，产出静态 index.html。

激活 = 出现在某个 workflow 的 `python main.py <job>` 调用里。
"""
import datetime as _dt
import re
from pathlib import Path

ROOT = Path(__file__).parent
WF_DIR = ROOT / ".github" / "workflows"
OUT_DIR = ROOT / "site"
OUT = OUT_DIR / "index.html"


def _active_jobs() -> dict[str, dict]:
    """返回 {workflow文件名: {name, cron, jobs:[...]}}。"""
    out: dict[str, dict] = {}
    for wf in sorted(WF_DIR.glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        name = re.search(r"^name:\s*(.+)$", text, re.M)
        cron = re.search(r"cron:\s*[\"']?([^\"'\s][^\"'\n]*)", text)
        jobs = re.findall(r"python\s+main\.py\s+(\w+)", text)
        if not jobs:
            continue  # 无业务 job 的 workflow（如 site.yml 自身）不展示
        out[wf.stem] = {
            "name": name.group(1).strip() if name else wf.stem,
            "cron": cron.group(1).strip() if cron else "",
            "jobs": jobs,
        }
    return out


def _render(active: dict[str, dict]) -> str:
    rows = []
    for wf, meta in active.items():
        chips = "".join(f'<span class="chip">{j}</span>' for j in meta["jobs"])
        rows.append(
            f'<section class="wf"><div class="wf-head">'
            f'<h2>{meta["name"]}</h2>'
            f'<span class="cron">{meta["cron"]}</span></div>'
            f'<div class="chips">{chips}</div></section>'
        )
    body = "\n".join(rows) if rows else '<p class="empty">暂无激活的 job</p>'
    return f"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cyber Scout</title>
<style>
:root {{ --bg:#0b0e14; --panel:#131826; --fg:#e6e9f0; --muted:#8a93a6; --accent:#4ff0c8; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:720px; margin:0 auto; padding:40px 20px; }}
h1 {{ font-size:24px; margin:0 0 4px; }}
.sub {{ color:var(--muted); font-size:13px; margin-bottom:28px; }}
.wf {{ background:var(--panel); border:1px solid #222a3d; border-radius:10px; padding:16px 18px; margin-bottom:14px; }}
.wf-head {{ display:flex; align-items:baseline; justify-content:space-between; gap:12px; }}
h2 {{ font-size:16px; margin:0; }}
.cron {{ color:var(--muted); font-family:ui-monospace,Consolas,monospace; font-size:12px; }}
.chips {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }}
.chip {{ color:var(--accent); border:1px solid var(--accent); border-radius:999px; padding:4px 12px; font-size:13px; }}
.empty {{ color:var(--muted); }}
</style>
</head>
<body><main>
<h1>Cyber Scout</h1>
<div class="sub">激活的 Job · 更新于 {_dt.datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
{body}
</main></body></html>"""


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    OUT.write_text(_render(_active_jobs()), encoding="utf-8")


if __name__ == "__main__":
    main()
