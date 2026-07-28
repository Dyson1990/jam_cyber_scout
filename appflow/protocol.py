"""
JSONL 协议工具
=============
定义 App 之间数据交换的标准格式：每行一个 JSON 对象。
"""

import json
import sys
from collections.abc import Iterator
from typing import Any


def read_jsonl(stream=sys.stdin) -> list[dict[str, Any]]:
    """从流中读取全部 JSONL 行，返回 dict 列表。"""
    items: list[dict[str, Any]] = []
    for line in stream:
        line = line.strip()
        if not line:
            continue
        items.append(json.loads(line))
    return items


def read_jsonl_iter(stream=sys.stdin) -> Iterator[dict[str, Any]]:
    """流式读取 JSONL，逐行 yield，适合大数据量场景。"""
    for line in stream:
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)


def write_jsonl(items: list[dict[str, Any]], stream=sys.stdout) -> None:
    """将 dict 列表写入流，每行一个 JSON。"""
    for item in items:
        stream.write(json.dumps(item, ensure_ascii=False) + "\n")
    stream.flush()


def write_one(item: dict[str, Any], stream=sys.stdout) -> None:
    """写入单条记录并刷新。"""
    stream.write(json.dumps(item, ensure_ascii=False) + "\n")
    stream.flush()
