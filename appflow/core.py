"""
AppFlow 核心引擎
===============
负责按顺序串联 App，将上一个 App 的 stdout(JSONL) 管道传递给下一个 App 的 stdin。
"""

import asyncio
import logging
import time
from typing import Any

from appflow.process import AppProcess

logger = logging.getLogger(__name__)


class Pipeline:
    """App 流水线。

    用法:
        pipeline = Pipeline()
        pipeline.add("scrapy_app", ["python", "apps/scrapy_app/main.py", "movie"])
        pipeline.add("analyzer_app", ["python", "apps/analyzer_app/main.py"])
        pipeline.add("notifier", ["python", "apps/notifier/main.py"])
        await pipeline.run()
    """

    def __init__(self):
        self._stages: list[tuple[str, list[str]]] = []

    def add(self, name: str, cmd: list[str]) -> None:
        """往流水线末尾添加一个 App。"""
        self._stages.append((name, cmd))

    async def run(self) -> list[dict[str, Any]]:
        """按顺序执行所有 App，返回最后一个 App 的输出。"""
        if not self._stages:
            logger.warning("流水线为空，无任务执行")
            return []

        data: list[dict[str, Any]] | None = None

        total = len(self._stages)
        for i, (name, cmd) in enumerate(self._stages, 1):
            logger.info(f"[{i}/{total}] 启动: {name} ({' '.join(cmd)})")
            t0 = time.perf_counter()

            proc = AppProcess(cmd)
            data = await proc.run(input_data=data)

            elapsed = time.perf_counter() - t0
            logger.info(f"[{i}/{total}] 完成: {name} → {len(data)} 条记录 ({elapsed:.2f}s)")

        return data or []
