"""Report App — 整理运行反馈
=============================
读 stdin 的 RunSummaryItem JSONL，整理成一条 ReportItem。

输入（由 main.py 生成）: RunSummaryItem
输出: ReportItem  → 交给 feishu 发送
"""

import sys

from appflow.item import ReportItem, RunSummaryItem


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    summary = None
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        summary = RunSummaryItem.loads(line)

    if summary is None:
        return  # 无输入，无输出

    ok = summary.status == "ok"
    stages = summary.stages

    title = f"{'✅' if ok else '❌'} {summary.job} {'成功' if ok else '失败'}"

    if ok:
        content = " · ".join(f"✅{s['stage']}" for s in stages) if stages else "无"
    else:
        lines = []
        for s in stages:
            icon = "✅" if s.get("status") == "ok" else "❌"
            lines.append(f"{icon} {s.get('stage')}")
            if s.get("error"):
                lines.append(str(s["error"]))
        content = "\n".join(lines)

    print(ReportItem(title=title, content=content).dumps())
    sys.stdout.flush()


if __name__ == "__main__":
    main()
