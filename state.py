"""
状态管理模块
=============
通过 state.json 持久化每次运行的状态，实现跨 GitHub Actions 运行的变化检测。

state.json 结构:
{
    "spider_security_news": {
        "last_hash": "abc123...",
        "last_count": 42,
        "last_run": "2026-07-26T09:00:00+08:00"
    },
    ...
}

设计考虑:
- 用每张 spider 表的"内容聚合 hash + 行数"来判断是否有新数据
- GitHub Cache 可能 miss（7 天未命中或 evict），miss 时当作首次运行
"""

import json
import logging
import os
from pathlib import Path

from config import STATE_FILE

logger = logging.getLogger(__name__)


def load_state() -> dict:
    """读取上次运行的状态。

    Returns:
        状态字典。如果文件不存在或损坏，返回空字典（视为首次运行）。
    """
    if not os.path.exists(STATE_FILE):
        logger.info("state.json 不存在，视为首次运行")
        return {}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        logger.info(f"已加载状态，包含 {len(state)} 个 spider 记录")
        return state
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"state.json 读取失败: {e}，视为首次运行")
        return {}


def save_state(state: dict) -> None:
    """保存当前运行状态到文件。

    GitHub Actions workflow 会在 save cache 步骤中将此文件上传。
    """
    Path(STATE_FILE).write_text(
        json.dumps(state, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info(f"状态已保存到 {STATE_FILE}")


def has_changed(table_key: str, new_hash: str, new_count: int, last_state: dict) -> bool:
    """判断 spider 表的数据是否相比上次有变化。

    Args:
        table_key: spider 表的标识（如 "spider_security_news"）
        new_hash: 本次所有数据的聚合 hash
        new_count: 本次数据行数
        last_state: 上次运行的状态字典

    Returns:
        True 表示有变化（或首次运行），False 表示无变化
    """
    prev = last_state.get(table_key)
    if prev is None:
        return True  # 首次运行，算作"有变化"

    if prev.get("last_hash") != new_hash:
        return True

    if prev.get("last_count") != new_count:
        return True

    return False
