"""
PushPlus 推送模块
==================
PushPlus API: GET https://www.pushplus.plus/send
"""

import logging

import requests

from config import PUSHPLUS_TOKEN

logger = logging.getLogger(__name__)

API_URL = "https://www.pushplus.plus/send"


def send(title: str, content: str, template: str = "html") -> bool:
    """推送消息到微信。"""
    if not PUSHPLUS_TOKEN:
        logger.warning("PUSHPLUS_TOKEN 未设置，跳过推送")
        return False

    try:
        r = requests.get(
            API_URL,
            params={
                "token": PUSHPLUS_TOKEN,
                "title": title,
                "content": content,
                "template": template,
            },
            timeout=15,
        )
        result = r.json()
        code = result.get("code", -1)
        if code == 200:
            logger.info(f"PushPlus 推送成功: {title}")
            return True
        else:
            logger.error(f"PushPlus 返回错误: code={code}, msg={result.get('msg')}")
            return False
    except requests.RequestException as e:
        logger.error(f"PushPlus 请求失败: {e}")
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
