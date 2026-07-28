"""
AppFlow CLI Pipeline
====================
用法:
    python main.py <job名称>      # 运行指定 Job
    python main.py                # 列出 config.py 中所有 Job
"""

import asyncio
import logging
import sys

from appflow.core import Pipeline
from config import jobs


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if len(sys.argv) < 2:
        print("可用的 Job:\n")
        for name, stages in jobs.items():
            apps = " | ".join(app for app, _ in stages)
            print(f"  {name:20s}  →  {apps}")
        print(f"\n运行: python main.py <job名称>")
        sys.exit(0)

    job_name = sys.argv[1]
    stages = jobs.get(job_name)
    if stages is None:
        print(f"未知 Job: {job_name}", file=sys.stderr)
        print(f"可用的 Job: {', '.join(jobs.keys())}", file=sys.stderr)
        sys.exit(1)

    pipeline = Pipeline()
    for name, args in stages:
        cmd = [sys.executable, "-m", f"apps.{name}.main"] + args
        pipeline.add(name, cmd)

    asyncio.run(pipeline.run())


if __name__ == "__main__":
    main()
