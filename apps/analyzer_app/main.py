"""
Analyzer App — 数据分析
=======================
从 stdin 读取 JSONL，分析处理后输出新的 JSONL 到 stdout。

用法: python -m apps.analyzer_app.main [--model gpt4]
"""

import json
import sys
from datetime import datetime, timezone


def analyze(item: dict) -> dict:
    """对单条记录进行分析，返回增强后的 dict。"""
    title = item.get("title", "")

    # 模拟分析逻辑
    score = len(title) * 7 % 100  # 基于标题长度的伪评分
    tags = []
    if "matrix" in title.lower():
        tags.append("科幻")
    if "inception" in title.lower():
        tags.append("梦境")
    if "interstellar" in title.lower():
        tags.append("太空")
    if "ai" in title.lower() or "智" in title.lower():
        tags.append("AI")
    if "安全" in title.lower() or "security" in title.lower():
        tags.append("安全")

    return {
        "type": f"{item.get('type', 'unknown')}_analysis",
        "title": title,
        "url": item.get("url", ""),
        "score": score,
        "tags": tags,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    # 命令行参数仅用于配置，不用于业务数据
    model = "default"
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--model" and i + 1 < len(args):
            model = args[i + 1]

    if model != "default":
        print(f"[analyzer] 使用模型: {model}", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            print(f"[analyzer] 跳过无效 JSON: {line[:80]}", file=sys.stderr)
            continue

        result = analyze(item)
        print(json.dumps(result, ensure_ascii=False))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
