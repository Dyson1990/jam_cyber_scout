"""
Notifier App — PushPlus 推送
============================
从 stdin 读取 JSONL，拼接成 HTML 消息后通过 PushPlus 推送。
兼容 Pipeline 模式（stdin JSONL）和独立命令行模式（-t/-m 参数）。

Pipeline 用法:
    echo '{"title":"test","score":90}' | python apps/notifier/notifier.py

独立用法:
    python apps/notifier/notifier.py -t "标题" -m "消息内容"
"""

import argparse
import json
import os
import sys
import time

import requests

API_URL = "http://www.pushplus.plus/send"


def send(title: str, content: str, template: str = "html") -> bool:
    token = os.getenv("PUSHPLUS_TOKEN", "")
    if not token:
        print("PUSHPLUS_TOKEN 未设置", file=sys.stderr)
        return False

    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": template,
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    for attempt in (1, 2):
        try:
            resp = requests.post(API_URL, data=body, headers=headers, timeout=15)
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 200:
                    print(f"推送成功: {title}", file=sys.stderr)
                    return True
                else:
                    print(f"PushPlus 错误: {result.get('msg')}", file=sys.stderr)
                    return False
            elif resp.status_code == 504 and attempt == 1:
                print("PushPlus 504，10 分钟后重试...", file=sys.stderr)
                time.sleep(600)
            else:
                print(f"HTTP {resp.status_code}", file=sys.stderr)
                return False
        except requests.RequestException as e:
            if attempt == 1:
                print(f"请求失败: {e}，10 分钟后重试...", file=sys.stderr)
                time.sleep(600)
            else:
                print(f"重试仍失败: {e}", file=sys.stderr)
                return False
    return False


def build_html(items: list[dict]) -> str:
    """将 JSONL 数据拼接为 HTML 表格消息，自动适配字段。"""
    if not items:
        return "<p>无数据</p>"

    # 收集所有字段名，过滤掉内部字段
    skip_keys = {"type", "analyzed_at"}
    all_keys = []
    for item in items:
        for k in item:
            if k not in skip_keys and k not in all_keys:
                all_keys.append(k)

    if not all_keys:
        return f"<pre>{json.dumps(items, ensure_ascii=False, indent=2)}</pre>"

    head = "<tr>" + "".join(f"<th>{k}</th>" for k in all_keys) + "</tr>"
    body = []
    for item in items:
        cells = []
        for k in all_keys:
            v = item.get(k, "")
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            elif v is None:
                v = "-"
            # url 字段转为链接
            if k == "url" and v:
                title = item.get("title", v)
                cells.append(f'<td><a href="{v}">{title}</a></td>')
            else:
                cells.append(f"<td>{v}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")

    return (
        "<table border='1' cellpadding='4' cellspacing='0'>"
        + head
        + "".join(body)
        + "</table>"
    )


def run_pipeline() -> int:
    """Pipeline 模式：从 stdin 读取 JSONL，发送通知，输出结果到 stdout。"""
    items: list[dict] = []
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"跳过无效 JSON: {line[:80]}", file=sys.stderr)

    if not items:
        print("无输入数据，跳过推送", file=sys.stderr)
        return 0

    html = build_html(items)
    count = len(items)
    title = f"Cyber Scout - {count} 条新结果"

    ok = send(title, html)
    # 输出结果到 stdout，供下游 App 读取
    print(json.dumps({"notified": ok, "count": count}, ensure_ascii=False))
    return 0 if ok else 1


def run_standalone() -> int:
    """独立模式：通过 -t/-m 参数调用。"""
    parser = argparse.ArgumentParser(description="PushPlus 推送")
    parser.add_argument("-t", "--title", required=True, help="消息标题")
    parser.add_argument("-m", "--message", required=True, help="消息内容（支持 HTML）")
    args = parser.parse_args()

    ok = send(args.title, args.message)
    return 0 if ok else 1


def main():
    # 判断模式：如果有命令行参数 -t/-m，走独立模式；否则走 pipeline 模式
    has_cli_args = any(arg in sys.argv for arg in ("-t", "--title", "-m", "--message"))
    if has_cli_args:
        code = run_standalone()
    else:
        code = run_pipeline()
    sys.exit(code)


if __name__ == "__main__":
    main()
