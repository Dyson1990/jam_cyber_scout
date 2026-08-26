"""植物状态读写 — species/plans/plants.json 分开存，GitHub Action 定时跑并 git 提交。"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent


def load(name: str):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def save(name: str, data) -> None:
    with open(DATA_DIR / name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
