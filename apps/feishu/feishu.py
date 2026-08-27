"""飞书通信 App — 自建应用 API，读 stdin JSONL 请求，执行后输出结果。

操作契约（每行一个 JSON）:
    请求 {"op":"send","ref":"<id>","chat_id":"oc_xxx","text":"..."}
        → 输出 {"op":"sent","ref":"<id>","message_id":"om_xxx"}
    请求 {"op":"check","ref":"<id>","message_id":"om_xxx"}
        → 输出 {"op":"checked","ref":"<id>","reacted":bool,"action_time":毫秒}

列群: python -m apps.feishu.feishu --list-chats
环境变量: FEISHU_APP_ID / FEISHU_APP_SECRET
"""

import json
import os
import sys
import time

import requests

TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
MSG_URL = "https://open.feishu.cn/open-apis/im/v1/messages"
CHATS_URL = "https://open.feishu.cn/open-apis/im/v1/chats"

_cache = {"token": "", "expire": 0.0}


def get_token() -> str:
    now = time.time()
    if _cache["token"] and now < _cache["expire"]:
        return _cache["token"]
    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        raise RuntimeError("缺少 FEISHU_APP_ID / FEISHU_APP_SECRET 环境变量")
    resp = requests.post(TOKEN_URL, json={"app_id": app_id, "app_secret": app_secret}, timeout=15)
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 tenant_access_token 失败: {data}")
    _cache["token"] = data["tenant_access_token"]
    _cache["expire"] = now + data.get("expire", 7200) - 60
    return _cache["token"]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json; charset=utf-8",
    }


def send_text(chat_id: str, text: str) -> str:
    payload = {"receive_id": chat_id, "msg_type": "text", "content": json.dumps({"text": text})}
    resp = requests.post(
        MSG_URL, params={"receive_id_type": "chat_id"}, json=payload, headers=_headers(), timeout=15
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"发送消息失败: {data}")
    return data["data"]["message_id"]


def reaction_time(message_id: str) -> int | None:
    """返回消息上首个表情的点赞时间（毫秒时间戳），无表情返回 None。"""
    resp = requests.get(
        f"{MSG_URL}/{message_id}/reactions", params={"user_id_type": "open_id"}, headers=_headers(), timeout=15
    )
    data = resp.json()
    if data.get("code") != 0:
        return None  # 消息撤回/无权限等，按未确认处理
    items = data.get("data", {}).get("items", [])
    if not items:
        return None
    return int(items[0].get("action_time", 0))


def list_chats() -> list[dict]:
    resp = requests.get(CHATS_URL, params={"page_size": 100}, headers=_headers(), timeout=15)
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取群列表失败: {data}")
    return data.get("data", {}).get("items", [])


def send_webhook(hook: str, text: str) -> None:
    """群机器人 webhook 发文本消息，无需自建应用 token。"""
    resp = requests.post(hook, json={"msg_type": "text", "content": {"text": text}}, timeout=15)
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"webhook 发送失败: {data}")


def webhook_main(hook: str) -> int:
    """webhook 模式：读 stdin 的 {title, content} 消息，逐条发送。"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            print(f"feishu 跳过无效 JSON: {line[:80]}", file=sys.stderr)
            continue
        title = item.get("title", "")
        content = item.get("content") or item.get("text") or ""
        text = f"{title}\n{content}" if title else content
        try:
            send_webhook(hook, text)
        except RuntimeError as e:
            print(f"feishu webhook 失败: {e}", file=sys.stderr)
        sys.stdout.flush()
    return 0


def main() -> int:
    # webhook 地址是配置（env），配置了就发群机器人；否则走自建应用
    hook = os.getenv("FEISHU_WEBHOOK", "")
    if hook:
        return webhook_main(hook)

    if "--list-chats" in sys.argv:
        try:
            for c in list_chats():
                print(f"{c.get('chat_id')}  {c.get('name')}")
        except RuntimeError as e:
            print(e, file=sys.stderr)
            return 1
        return 0

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            op = req.get("op")
            if op == "send":
                msg_id = send_text(req["chat_id"], req["text"])
                print(json.dumps({"op": "sent", "ref": req.get("ref"), "message_id": msg_id}, ensure_ascii=False))
            elif op == "check":
                t = reaction_time(req.get("message_id"))
                print(json.dumps({"op": "checked", "ref": req.get("ref"), "reacted": t is not None, "action_time": t}, ensure_ascii=False))
            else:
                print(f"未知 op: {op}", file=sys.stderr)
        except (RuntimeError, KeyError) as e:
            print(f"feishu 处理失败: {e}", file=sys.stderr)
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
