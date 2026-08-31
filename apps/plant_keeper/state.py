"""植物状态读写 — 单一 state.json，GitHub Action 定时跑并 git 提交。"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent
STATE_FILE = "state.json"


def load() -> dict:
    with open(DATA_DIR / STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save(data: dict) -> None:
    with open(DATA_DIR / STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
