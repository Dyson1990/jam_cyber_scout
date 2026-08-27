"""DeepSeek App — 用 langchain 调 DeepSeek，逐条读 stdin JSONL 并回复。

数据契约：每行一个 JSON，取 prompt/text 字段作为提问（缺省则总结整条），
输出在原 JSON 上追加 reply 字段。

用法: python -m apps.deepseek.entry
环境变量: DEEPSEEK_API_KEY
"""

import json
import os
import sys

from langchain_deepseek import ChatDeepSeek

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def main() -> int:
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("缺少 DEEPSEEK_API_KEY 环境变量", file=sys.stderr)
        return 1

    llm = ChatDeepSeek(model="deepseek-chat", api_key=api_key)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            print(f"[deepseek] 跳过无效 JSON: {line[:80]}", file=sys.stderr)
            continue

        prompt = item.get("prompt") or item.get("text")
        if not prompt:
            prompt = f"用一句话总结：{json.dumps(item, ensure_ascii=False)}"

        try:
            reply = llm.invoke(prompt).content
        except Exception as e:
            print(f"[deepseek] 调用失败: {e}", file=sys.stderr)
            continue

        out = dict(item)
        out["reply"] = reply
        print(json.dumps(out, ensure_ascii=False))
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
