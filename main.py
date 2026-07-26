"""
jam_cyber_scout 主入口
======================
在 GitHub Actions 中由 workflow 调用，执行一次完整流程：

  1. 连接 Eden Crawler 的 data.db
  2. 读取上次状态 (state.json)
  3. 对比各 spider 表的数据变化
  4. 有新增/变化 → 构建推送消息 → 调用 PushPlus
  5. 保存新状态

本地测试:
  set PUSHPLUS_TOKEN=your_token
  python main.py
"""

import hashlib
import json
import logging
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from config import (
    EDEN_CRAWLER_DIR,
    EDEN_DB_PATH,
    SPIDER_NAMES,
    KEYWORDS,
    MAX_ALERT_ITEMS,
)
from notifier import send, build_alert_message
from state import load_state, save_state, has_changed

# 北京时间
TZ_BEIJING = timezone(timedelta(hours=8))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jam_cyber_scout")


def get_db_path() -> Path:
    """获取 Eden Crawler 的 data.db 路径。"""
    db_path = Path(EDEN_CRAWLER_DIR) / EDEN_DB_PATH
    if not db_path.exists():
        logger.error(f"数据库文件不存在: {db_path}")
        sys.exit(1)
    return db_path


def get_spider_tables(db_path: Path) -> list[str]:
    """获取 data.db 中所有 spider_* 表名。"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'spider_%'"
    )
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    logger.info(f"发现 {len(tables)} 个 spider 表: {tables}")
    return tables


def compute_table_hash(cursor, table_name: str) -> tuple[str, int]:
    """计算一张表的内容聚合 hash 和行数。

    取所有行的文本字段拼接后计算 SHA256，忽略 BLOB 字段。
    """
    # 获取列名
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = [row[1] for row in cursor.fetchall()]
    # 排除 id 和 insert_time 列，以及可能的 BLOB 列
    text_cols = [c for c in cols if c not in ("id", "insert_time")]

    if not text_cols:
        return "", 0

    # 选取所有文本列
    col_expr = ", ".join(f'COALESCE(CAST("{c}" AS TEXT), "")' for c in text_cols)
    cursor.execute(f"SELECT {col_expr} FROM {table_name} ORDER BY id")
    rows = cursor.fetchall()

    h = hashlib.sha256()
    for row in rows:
        for val in row:
            h.update(str(val).encode("utf-8", errors="replace"))
            h.update(b"\x00")  # 列分隔符

    return h.hexdigest(), len(rows)


def get_sample_items(cursor, table_name: str, limit: int = 5) -> list[dict]:
    """从表中获取最新几条样例数据。"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = [row[1] for row in cursor.fetchall()]

    cursor.execute(
        f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT {limit}"
    )
    rows = cursor.fetchall()
    samples = []
    for row in rows:
        item = {}
        for col_name, val in zip(cols, row):
            if isinstance(val, bytes):
                item[col_name] = f"<BLOB, {len(val)} bytes>"
            else:
                item[col_name] = str(val)[:200] if val else ""
        samples.append(item)
    return samples


def check_keywords(samples: list[dict]) -> list[str]:
    """检查样例数据中命中的关键词。"""
    hit = set()
    for item in samples:
        text = json.dumps(item, ensure_ascii=False).lower()
        for kw in KEYWORDS:
            if kw.lower() in text:
                hit.add(kw)
    return sorted(hit)


def filter_spider_tables(tables: list[str]) -> list[str]:
    """如果 SPIDER_NAMES 指定了目标，只保留对应的表。"""
    if not SPIDER_NAMES:
        return tables
    target_tables = {f"spider_{name}" for name in SPIDER_NAMES}
    return [t for t in tables if t in target_tables]


def main():
    logger.info("=" * 50)
    logger.info("jam_cyber_scout 开始运行")
    logger.info("=" * 50)

    # 1. 连接数据库
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 2. 获取 spider 表列表
    tables = get_spider_tables(db_path)
    tables = filter_spider_tables(tables)
    if not tables:
        logger.warning("没有找到 spider 表，退出")
        conn.close()
        return

    # 3. 读取上次状态
    last_state = load_state()

    # 4. 逐表对比
    now = datetime.now(TZ_BEIJING).isoformat(timespec="seconds")
    new_state = {}
    alerts = []

    for table in tables:
        table_hash, row_count = compute_table_hash(cursor, table)
        spider_name = table.replace("spider_", "", 1)

        logger.info(f"检查 {spider_name}: hash={table_hash[:16]}..., rows={row_count}")

        if not has_changed(table, table_hash, row_count, last_state):
            logger.info(f"  {spider_name}: 无变化，跳过")
            new_state[table] = last_state[table]
            continue

        # 有变化！获取详情
        prev = last_state.get(table, {})
        prev_count = prev.get("last_count", 0)
        sample_items = get_sample_items(cursor, table, limit=MAX_ALERT_ITEMS)
        hits = check_keywords(sample_items)

        logger.info(f"  {spider_name}: 有变化！上次 {prev_count} 行 → 本次 {row_count} 行")
        if hits:
            logger.info(f"  命中关键词: {hits}")

        alerts.append({
            "table": table,
            "spider_name": spider_name,
            "new_count": row_count,
            "changed_count": row_count - prev_count if prev_count else row_count,
            "samples": sample_items,
            "keywords": hits,
        })

        new_state[table] = {
            "last_hash": table_hash,
            "last_count": row_count,
            "last_run": now,
        }

    conn.close()

    # 5. 推送
    if not alerts:
        logger.info("所有 spider 均无变化，不推送")
        # 仍然保存状态（主要是首次运行的情况）
        if not last_state:
            save_state(new_state)
        return

    # 构建推送消息
    message_lines = [
        f"# 🔔 Cyber Scout 情报简报",
        f"",
        f"**扫描时间**: {now}",
        f"**监控站点**: {len(alerts)} 个有更新",
        f"",
        "---",
        "",
    ]

    all_keywords = set()
    for a in alerts:
        all_keywords.update(a["keywords"])
        message_lines.append(
            build_alert_message(
                a["spider_name"],
                a["new_count"],
                a["changed_count"],
                a["samples"],
                a["keywords"],
            )
        )
        message_lines.append("---")
        message_lines.append("")

    # 标题：加关键词标签
    title_parts = ["🔔 Cyber Scout"]
    if all_keywords:
        kw_str = "、".join(sorted(all_keywords)[:5])
        title_parts.append(f"命中: {kw_str}")
    title = " · ".join(title_parts)

    message = "\n".join(message_lines)

    # 限制消息长度（PushPlus 有长度限制，保守取 5000 字）
    if len(message) > 5000:
        message = message[:4900] + "\n\n... (内容过长，已截断)"

    logger.info(f"推送消息长度: {len(message)} 字符")
    success = send(title, message)

    if success:
        logger.info("推送成功 ✓")
    else:
        logger.warning("推送失败，但继续保存状态")

    # 6. 保存状态
    save_state(new_state)
    logger.info("jam_cyber_scout 运行完毕")


if __name__ == "__main__":
    main()
