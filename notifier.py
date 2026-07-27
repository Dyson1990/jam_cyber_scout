"""
PushPlus 推送模块
==================
PushPlus API: POST http://www.pushplus.plus/send
"""

import json
import logging
import time

import requests

from config import PUSHPLUS_TOKEN

logger = logging.getLogger(__name__)

API_URL = "http://www.pushplus.plus/send"


def send(title: str, content: str, template: str = "html") -> bool:
    """推送消息到微信。504 时等待 10 分钟后重试一次。"""
    if not PUSHPLUS_TOKEN:
        logger.warning("PUSHPLUS_TOKEN 未设置，跳过推送")
        return False

    payload = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": template,
    }
    body = json.dumps(payload).encode(encoding="utf-8")
    headers = {"Content-Type": "application/json"}

    for attempt in (1, 2):
        try:
            resp = requests.post(API_URL, data=body, headers=headers, timeout=15)
            if resp.status_code == 200:
                result = resp.json()
                code = result.get("code", -1)
                if code == 200:
                    logger.info(f"PushPlus 推送成功: {title}")
                    return True
                else:
                    logger.error(f"PushPlus 返回错误: code={code}, msg={result.get('msg')}")
                    return False
            elif resp.status_code == 504 and attempt == 1:
                logger.warning("PushPlus 504，等待 10 分钟后重试...")
                time.sleep(600)
            else:
                logger.error(f"PushPlus HTTP {resp.status_code}: {resp.text[:200]}")
                return False
        except requests.RequestException as e:
            if attempt == 1:
                logger.warning(f"PushPlus 请求失败: {e}，等待 10 分钟后重试...")
                time.sleep(600)
            else:
                logger.error(f"PushPlus 重试仍失败: {e}")
                return False

    return False


def build_alert_message(
    spider_name: str,
    new_count: int,
    changed_count: int,
    sample_items: list[dict],
    keywords: list[str],
) -> str:
    """构建单条 Spider 的推送消息正文（HTML 格式）。"""
    lines = [
        f"<h2>🕵️ {spider_name}</h2>",
        f"<p><b>新增条目</b>: {new_count}<br>"
        f"<b>变化条目</b>: {changed_count}</p>",
    ]

    if keywords:
        lines.append(f"<p><b>命中关键词</b>: {', '.join(keywords)}</p>")

    if sample_items:
        lines.append("<h3>📋 样例</h3><ul>")
        for i, item in enumerate(sample_items[:5], 1):
            # IP 类数据特殊展示
            if "ip" in item:
                ip = item.get("ip", "")
                country = item.get("country", "")
                city = item.get("city", "")
                org = item.get("org", "")
                lines.append(
                    f"<li><b>{ip}</b> — {country} {city}<br>"
                    f"<small>ISP: {org}</small></li>"
                )
            else:
                name = item.get("name", f"条目 #{i}")
                url = item.get("url", "")
                if url:
                    lines.append(f'<li><a href="{url}">{name}</a></li>')
                else:
                    lines.append(f"<li>{name}</li>")
        lines.append("</ul>")

    return "\n".join(lines)


if __name__ == "__main__":
    send("Cyber Scout 测试", "通道测试消息")
