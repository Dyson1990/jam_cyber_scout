"""飞书多维表格同步 — 双向：Bitable 是唯一数据源，state.json 仅作备份。

load: 读「状态」表整份 JSON 回写 state.json（表为空则保留现有 state.json）。
save: 把 state.json 整份写进「状态」表，再刷新 4 张只读视图（植物/肥料/设备/历史）。
视图幂等：先清空再重建，保证与 state.json 完全一致。

环境变量: BITABLE_APP_ID / BITABLE_APP_SECRET（专用新应用）
参数: app_token 由 job 经命令行传入（["bitable","load","<app_token>"] / ["bitable","save","<app_token>"]）
"""

import json
import os
import sys

import requests

from apps.plant_keeper import state

BASE = "https://open.feishu.cn/open-apis/bitable/v1"
TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"

# 字段类型: 1 文本 2 数字 7 复选框
TABLES = {
    "state": {
        "name": "状态",
        "fields": [
            {"field_name": "json", "type": 1},
        ],
    },
    "plants": {
        "name": "植物",
        "fields": [
            {"field_name": "id", "type": 1},
            {"field_name": "名称", "type": 1},
            {"field_name": "位置", "type": 1},
            {"field_name": "栽培方式", "type": 1},
            {"field_name": "自动浇水", "type": 7},
            {"field_name": "下次浇水", "type": 1},
            {"field_name": "上次浇水", "type": 1},
            {"field_name": "下次施肥", "type": 1},
            {"field_name": "最近施肥", "type": 1},
            {"field_name": "施肥次数", "type": 2},
            {"field_name": "施肥方案", "type": 1},
            {"field_name": "施肥依据", "type": 1},
            {"field_name": "养护建议", "type": 1},
        ],
    },
    "fertilizers": {
        "name": "肥料",
        "fields": [
            {"field_name": "id", "type": 1},
            {"field_name": "名称", "type": 1},
            {"field_name": "备注", "type": 1},
            {"field_name": "记录方式", "type": 1},
            {"field_name": "条码值", "type": 1},
        ],
    },
    "device": {
        "name": "设备设置",
        "fields": [
            {"field_name": "阀门数", "type": 2},
            {"field_name": "每阀ml", "type": 2},
            {"field_name": "间隔天数", "type": 2},
            {"field_name": "输水秒数", "type": 2},
            {"field_name": "配肥容器ml", "type": 2},
        ],
    },
    "history": {
        "name": "历史流水",
        "fields": [
            {"field_name": "时间", "type": 1},
            {"field_name": "植物", "type": 1},
            {"field_name": "类型", "type": 1},
        ],
    },
}


def _get_token() -> str:
    app_id = os.getenv("BITABLE_APP_ID", "")
    app_secret = os.getenv("BITABLE_APP_SECRET", "")
    if not app_id or not app_secret:
        raise RuntimeError("缺少 BITABLE_APP_ID / BITABLE_APP_SECRET 环境变量")
    resp = requests.post(TOKEN_URL, json={"app_id": app_id, "app_secret": app_secret}, timeout=15)
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 tenant_access_token 失败: {data}")
    return data["tenant_access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}


def _get(token: str, url: str) -> dict:
    resp = requests.get(url, headers=_headers(token), timeout=15).json()
    if resp.get("code") != 0:
        raise RuntimeError(f"GET {url} 失败: {resp}")
    return resp.get("data", {})


def _post(token: str, url: str, body: dict) -> dict:
    resp = requests.post(url, json=body, headers=_headers(token), timeout=30).json()
    if resp.get("code") != 0:
        raise RuntimeError(f"POST {url} 失败: {resp}")
    return resp.get("data", {})


def _list_tables(app_token: str, token: str) -> dict:
    data = _get(token, f"{BASE}/apps/{app_token}/tables")
    return {t["name"]: t["table_id"] for t in data.get("items", [])}


def _create_table(app_token: str, token: str, name: str, fields: list) -> str:
    data = _post(token, f"{BASE}/apps/{app_token}/tables", {"table": {"name": name, "fields": fields}})
    return data["table_id"]


def _ensure_fields(app_token: str, token: str, table_id: str, fields: list) -> None:
    data = _get(token, f"{BASE}/apps/{app_token}/tables/{table_id}/fields")
    existing = {f["field_name"] for f in data.get("items", [])}
    for f in fields:
        if f["field_name"] not in existing:
            _post(token, f"{BASE}/apps/{app_token}/tables/{table_id}/fields", f)


def _ensure_schema(app_token: str, token: str) -> dict:
    """确保 5 张表存在且字段齐全，返回 {key: table_id}（每次按名称发现，不落盘）。"""
    tables = _list_tables(app_token, token)
    tid = {}
    for key, spec in TABLES.items():
        table_id = tables.get(spec["name"])
        if not table_id:
            table_id = _create_table(app_token, token, spec["name"], spec["fields"])
        _ensure_fields(app_token, token, table_id, spec["fields"])
        tid[key] = table_id
    return tid


def _put(fields: dict, key: str, val) -> None:
    if val is not None and val != "":
        fields[key] = val


def _plant_rows(s: dict) -> list:
    rows = []
    for p in s["plants"]:
        fh = p.get("fertilize_history") or []
        cn = p.get("care_note")
        care = cn[1] if isinstance(cn, list) and len(cn) >= 2 else None
        fields = {"自动浇水": bool(p.get("auto_water")), "施肥次数": len(fh)}
        _put(fields, "id", p.get("id"))
        _put(fields, "名称", p.get("name"))
        _put(fields, "位置", p.get("location"))
        _put(fields, "栽培方式", p.get("cultivation"))
        _put(fields, "下次浇水", p.get("next_water"))
        _put(fields, "上次浇水", p.get("last_watered"))
        _put(fields, "下次施肥", p.get("next_fertilize"))
        _put(fields, "最近施肥", fh[-1] if fh else None)
        _put(fields, "施肥方案", p.get("fertilizer_use"))
        _put(fields, "施肥依据", p.get("fertilize_reason"))
        _put(fields, "养护建议", care)
        rows.append(fields)
    return rows


def _fertilizer_rows(s: dict) -> list:
    rows = []
    for f in s["fertilizers"]:
        fields = {}
        _put(fields, "id", f.get("id"))
        _put(fields, "名称", f.get("name"))
        _put(fields, "备注", f.get("note"))
        _put(fields, "记录方式", f.get("record_type"))
        _put(fields, "条码值", f.get("value"))
        rows.append(fields)
    return rows


def _device_rows(s: dict) -> list:
    d = s.get("device", {})
    fields = {}
    _put(fields, "阀门数", d.get("valves"))
    _put(fields, "每阀ml", d.get("ml_per_valve"))
    _put(fields, "间隔天数", d.get("interval_days"))
    _put(fields, "输水秒数", d.get("water_duration"))
    _put(fields, "配肥容器ml", s.get("mix_container_ml"))
    return [fields]


def _history_rows(s: dict) -> list:
    rows = []
    for h in s.get("history", []):
        fields = {}
        _put(fields, "时间", h.get("time"))
        _put(fields, "植物", h.get("plant_name"))
        _put(fields, "类型", "浇水" if h.get("action") == "water" else "施肥")
        rows.append(fields)
    return rows


def _list_records(app_token: str, table_id: str, token: str) -> list:
    records = []
    page_token = None
    while True:
        url = f"{BASE}/apps/{app_token}/tables/{table_id}/records?page_size=500"
        if page_token:
            url += f"&page_token={page_token}"
        data = _get(token, url)
        records.extend(data.get("items", []))
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
    return records


def _load_state(app_token: str, table_id: str, token: str) -> dict | None:
    """读「状态」表唯一记录的整份 JSON；表为空或损坏返回 None。"""
    records = _list_records(app_token, table_id, token)
    if not records:
        return None
    raw = records[0].get("fields", {}).get("json")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _save_state(app_token: str, table_id: str, token: str, s: dict) -> None:
    """把整份 state 以紧凑 JSON 写入「状态」表（单记录 upsert）。"""
    raw = json.dumps(s, ensure_ascii=False, separators=(",", ":"))
    records = _list_records(app_token, table_id, token)
    if records:
        _post(token, f"{BASE}/apps/{app_token}/tables/{table_id}/records/batch_update",
              {"records": [{"record_id": records[0]["record_id"], "fields": {"json": raw}}]})
    else:
        _post(token, f"{BASE}/apps/{app_token}/tables/{table_id}/records/batch_create",
              {"records": [{"fields": {"json": raw}}]})


def _refresh(app_token: str, table_id: str, token: str, rows: list) -> None:
    ids = [r["record_id"] for r in _list_records(app_token, table_id, token)]
    if ids:
        _post(token, f"{BASE}/apps/{app_token}/tables/{table_id}/records/batch_delete", {"records": ids})
    if rows:
        _post(token, f"{BASE}/apps/{app_token}/tables/{table_id}/records/batch_create",
              {"records": [{"fields": r} for r in rows]})


def _load(app_token: str) -> int:
    if not app_token:
        raise RuntimeError("缺少 bitable app_token 参数")
    token = _get_token()
    tid = _ensure_schema(app_token, token)
    data = _load_state(app_token, tid["state"], token)
    if data is None:
        print("[bitable] 状态表为空，保留现有 state.json", file=sys.stderr)
        return 0
    state.save(data)
    return 0


def _save(app_token: str) -> int:
    if not app_token:
        raise RuntimeError("缺少 bitable app_token 参数")
    s = state.load()
    token = _get_token()
    tid = _ensure_schema(app_token, token)
    _save_state(app_token, tid["state"], token, s)
    _refresh(app_token, tid["plants"], token, _plant_rows(s))
    _refresh(app_token, tid["fertilizers"], token, _fertilizer_rows(s))
    _refresh(app_token, tid["device"], token, _device_rows(s))
    _refresh(app_token, tid["history"], token, _history_rows(s))
    return 0


def main() -> int:
    try:
        if "load" in sys.argv:
            return _load(_arg("load"))
        return _save(_arg("bitable"))
    except Exception as e:
        print(f"[bitable] 同步失败: {e}", file=sys.stderr)
        return 1


def _arg(op: str) -> str:
    # args: ["bitable", "load", "<app_token>"] / ["bitable", "save", "<app_token>"]
    try:
        return sys.argv[sys.argv.index(op) + 1]
    except (ValueError, IndexError):
        return ""
