"""
AppFlow 核心引擎
===============
按顺序串联 App：上一个 App 的 stdout(JSONL) 经 Item 严格校验后，传给下一个 App 的 stdin。
"""

import asyncio
import logging
import time

from appflow.item import ItemValidationError
from appflow.process import AppProcess

logger = logging.getLogger(__name__)


class Pipeline:
    """App 流水线。

    每阶段: 运行 app → 读原始输出 → item_cls.loads() 严格校验转为 Item → 传给下一阶段。
    终结点阶段（item_cls=None）不校验输出，仅执行副作用（发消息/回写状态）。
    """

    def __init__(self):
        self._stages: list[tuple[str, list[str], type | None]] = []

    def add(self, name: str, cmd: list[str], item_cls: type | None = None) -> None:
        """往流水线末尾添加一个 App。item_cls 为该阶段输出的 Item 类型。"""
        self._stages.append((name, cmd, item_cls))

    async def run(self) -> tuple[list, list[dict]]:
        """按顺序执行所有 App，返回 (最后阶段 Item 列表, 各阶段结果摘要)。

        单个 App 失败（退出码非 0 / Item 校验失败）不中断整体，
        记录到摘要供 report 整理反馈。
        """
        if not self._stages:
            logger.warning("流水线为空，无任务执行")
            return [], []

        data: list | None = None
        report: list[dict] = []

        total = len(self._stages)
        for i, (name, cmd, item_cls) in enumerate(self._stages, 1):
            logger.info(f"[{i}/{total}] 启动: {name} ({' '.join(cmd)})")
            t0 = time.perf_counter()

            try:
                proc = AppProcess(cmd)
                raw = await proc.run(input_items=data)

                if item_cls is not None:
                    items = [item_cls.loads(line) for line in raw]
                    data = items
                else:
                    items = []
                    data = None

                elapsed = time.perf_counter() - t0
                logger.info(f"[{i}/{total}] 完成: {name} → {len(items)} 条记录 ({elapsed:.2f}s)")
                report.append({"stage": name, "status": "ok", "count": len(items), "error": None})
            except (RuntimeError, ItemValidationError) as e:
                elapsed = time.perf_counter() - t0
                logger.error(f"[{i}/{total}] 失败: {name} ({elapsed:.2f}s): {e}")
                report.append({"stage": name, "status": "error", "count": 0, "error": str(e)})
                data = None
                break

        return data or [], report
