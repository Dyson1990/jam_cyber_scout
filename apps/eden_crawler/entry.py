"""
Eden Crawler App — Scrapy 爬虫入口
==================================
用法:
    python -m apps.eden_crawler.main <spider> [scrapy_args...]

示例:
    python -m apps.eden_crawler.main car
    python -m apps.eden_crawler.main ip -a target=xxx

从 stdin 读取可选的种子数据（JSONL），启动 scrapy crawl，结果以 JSONL 输出到 stdout。
"""

import json
import os
import subprocess
import sys


def read_stdin_seeds() -> list[dict] | None:
    """如果 stdin 有数据，读取为种子列表；否则返回 None。"""
    # stdin 是否有数据取决于是否是管道连接的
    if sys.stdin.isatty():
        return None
    items = []
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"跳过无效 JSON: {line[:80]}", file=sys.stderr)
    return items if items else None


def main():
    if len(sys.argv) < 2:
        print("用法: python -m apps.eden_crawler.main <spider> [scrapy_args...]", file=sys.stderr)
        sys.exit(1)

    spider = sys.argv[1]
    extra_args = sys.argv[2:]

    # 读取上游传入的种子数据（如果有）
    seeds = read_stdin_seeds()
    if seeds:
        urls = [s.get("url") for s in seeds if s.get("url")]
        if urls:
            # 将种子 URL 通过 -a urls=... 传给 spider
            extra_args = ["-a", f"urls={','.join(urls)}"] + extra_args

    # scrapy 项目在 eden_crawler 子目录（即 submodule）
    project_dir = os.path.join(os.path.dirname(__file__), "eden_crawler")

    # extra_spiders/ 中的独立 spider 用 runspider，submodule 内的用 crawl
    extra_dir = os.path.join(os.path.dirname(__file__), "extra_spiders")
    spider_file = os.path.join(extra_dir, f"{spider}.py")
    if os.path.isfile(spider_file):
        cmd = [
            sys.executable, "-m", "scrapy", "runspider", spider_file,
            "-o", "-:jsonlines",
        ] + extra_args
    else:
        cmd = [
            sys.executable, "-m", "scrapy", "crawl", spider,
            "-o", "-:jsonlines",
        ] + extra_args

    proc = subprocess.run(cmd, cwd=project_dir)
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
