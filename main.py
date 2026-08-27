"""
AppFlow CLI Pipeline
====================
用法:
    python main.py <job名称>      # 运行指定 Job
    python main.py                # 列出 jobs/ 中所有 Job
"""

import asyncio
import importlib
import logging
import os
import pkgutil
import sys

import jobs as jobs_pkg
from appflow.core import Pipeline
from appflow.item import ReportItem, RunSummaryItem
from appflow.process import AppProcess
from config import TEST_MODE, FEISHU_WEBHOOK


def _available_jobs() -> list[str]:
    return sorted(
        m.name for m in pkgutil.iter_modules(jobs_pkg.__path__)
        if not m.name.startswith("_")
    )


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    available = _available_jobs()

    if len(sys.argv) < 2:
        print("可用的 Job:\n")
        for name in available:
            stages = importlib.import_module(f"jobs.{name}").STAGES
            apps = " | ".join(app for app, _, _ in stages)
            print(f"  {name:20s}  →  {apps}")
        print(f"\n运行: python main.py <job名称>")
        sys.exit(0)

    job_name = sys.argv[1]
    if job_name not in available:
        print(f"未知 Job: {job_name}", file=sys.stderr)
        print(f"可用的 Job: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)

    stages = importlib.import_module(f"jobs.{job_name}").STAGES

    pipeline = Pipeline()
    for name, args, item_cls in stages:
        cmd = [sys.executable, "-m", f"apps.{name}.entry"] + args
        pipeline.add(name, cmd, item_cls)

    data, report = asyncio.run(pipeline.run())
    ok = all(s["status"] == "ok" for s in report)

    if TEST_MODE:
        # 测试环境：每个 job 末尾追加 report → feishu，整理并发送反馈
        os.environ["FEISHU_WEBHOOK"] = FEISHU_WEBHOOK
        summary = [RunSummaryItem(
            job=job_name,
            status="ok" if ok else "error",
            count=len(data),
            stages=report,
        )]
        raw = asyncio.run(
            AppProcess([sys.executable, "-m", "apps.report.entry"]).run(input_items=summary)
        )
        if raw:
            msgs = [ReportItem.loads(line) for line in raw]
            asyncio.run(
                AppProcess([sys.executable, "-m", "apps.feishu.entry"]).run(input_items=msgs)
            )

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
