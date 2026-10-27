"""req_sync App 入口 — 扫描 GitHub 提交日志，命中 REQ-xxx 的需求自动标「已完成」回写飞书多维表格。

首个 App，无 stdin 输入：直接读飞书「Requirements」表 + GitHub 提交日志，回写后打印判定摘要。
环境变量: FEISHU_BITABLE_APP_ID / FEISHU_BITABLE_APP_SECRET / GITHUB_TOKEN(可选)；args: <需求表 app_token>
"""

import os
import re
import sys
import time

import requests

OPEN = "https://open.feishu.cn/open-apis"

# Windows 控制台默认 GBK，强制 UTF-8 避免中文输出报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def _http(method, url, token="", body=None, params=None):
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = "Bearer " + token
    resp = requests.request(method, url, json=body, params=params, headers=headers, timeout=30)
    if resp.status_code == 404:  # GitHub 分支不存在当作无提交
        return {"code": 404}
    resp.raise_for_status()
    return resp.json()


def _tenant_token(app_id, app_secret):
    d = _http("POST", OPEN + "/auth/v3/tenant_access_token/internal",
              body={"app_id": app_id, "app_secret": app_secret})
    return d["tenant_access_token"]


def _field_text(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return "".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in v)
    if isinstance(v, dict):
        return v.get("text", "")
    return str(v)


def _list_records(token, app_token, table_id):
    records = []
    page_token = ""
    while True:
        params = {"page_size": "100"}
        if page_token:
            params["page_token"] = page_token
        data = _http("GET", f"{OPEN}/bitable/v1/apps/{app_token}/tables/{table_id}/records",
                     token=token, params=params)["data"]
        records.extend(data.get("items", []))
        page_token = data.get("page_token", "")
        if not page_token:
            return records


def _github_commits(repo, branch, since_ms, gh_token):
    params = {"per_page": "100"}
    if branch:
        params["sha"] = branch
    if since_ms:
        params["since"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(since_ms / 1000))
    d = _http("GET", "https://api.github.com/repos/" + repo + "/commits",
              token=gh_token, params=params)
    if d.get("code") == 404:
        return []
    return [c["commit"]["message"] for c in d if c.get("commit", {}).get("message")]


def main() -> int:
    try:
        _run()
        return 0
    except Exception as e:
        print(f"[req_sync] 同步失败: {e}", file=sys.stderr)
        return 1


def _run() -> None:
    app_id = os.environ["FEISHU_BITABLE_APP_ID"]
    app_secret = os.environ["FEISHU_BITABLE_APP_SECRET"]
    app_token = sys.argv[1] if len(sys.argv) > 1 else ""  # 配置走 args（job 传入）
    gh_token = os.environ.get("GITHUB_TOKEN", "")

    token = _tenant_token(app_id, app_secret)

    tables = _http("GET", f"{OPEN}/bitable/v1/apps/{app_token}/tables", token=token)["data"]["items"]
    table = next(t for t in tables if t.get("name") == "Requirements")
    table_id = table["table_id"]

    completed = []
    for rec in _list_records(token, app_token, table_id):
        f = rec["fields"]
        if _field_text(f.get("status")) in ("已完成", "已取消"):
            continue
        req_id = _field_text(f.get("req_id"))
        repo = _field_text(f.get("repo"))
        branch = _field_text(f.get("branch"))
        if not req_id or not repo:
            continue

        msgs = _github_commits(repo, branch, f.get("updated_at") or 0, gh_token)
        if not msgs:
            continue

        # 编号前后不能是数字，避免 REQ-001 误命中 REQ-0010
        pat = re.compile(r"(^|[^0-9])" + re.escape(req_id) + r"([^0-9]|$)", re.IGNORECASE)
        if not any(pat.search(m) for m in msgs):
            continue

        _http("PUT", f"{OPEN}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{rec['record_id']}",
              token=token, body={"fields": {"status": "已完成", "updated_at": int(time.time() * 1000)}})
        completed.append(req_id + " " + _field_text(f.get("title")))

    # 日志走 stderr，stdout 留给数据管道（本 App 为终结点，无数据输出）
    print(f"完成判定: {len(completed)} 条 -> 已完成", file=sys.stderr)
    for c in completed:
        print("  " + c, file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
