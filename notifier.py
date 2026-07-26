"""
PushPlus 推送模块
==================
PushPlus API: POST http://www.pushplus.plus/send
文档: https://www.pushplus.plus/doc/guide/api.html
"""

import json
import logging
from urllib import request
from urllib.error import URLError

from config import PUSHPLUS_TOKEN

logger = logging.getLogger(__name__)

API_URL = "http://www.pushplus.plus/send"


def send(title: str, content: str, template: str = "markdown") -> bool:
    """推送消息到微信。

    Args:
        title: 消息标题（微信显示在通知栏）
        content: 消息正文，支持 markdown 格式
        template: 消息模板类型，默认 markdown

    Returns:
        True 表示发送成功，False 表示失败
    """
    if not PUSHPLUS_TOKEN:
        logger.warning("PUSHPLUS_TOKEN 未设置，跳过推送")
        return False

    payload = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": template,
    }

    try:
        req = request.Request(
            API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            code = result.get("code", -1)
            if code == 200:
                logger.info(f"PushPlus 推送成功: {title}")
                return True
            else:
                logger.error(f"PushPlus 返回错误: code={code}, msg={result.get('msg')}")
                return False
    except URLError as e:
        logger.error(f"PushPlus 网络请求失败: {e}")
        return False
    except Exception as e:
        logger.error(f"PushPlus 推送异常: {e}")
        return False


def build_alert_message(
    spider_name: str,
    new_count: int,
    changed_count: int,
    sample_items: list[dict],
    keywords: list[str],
) -> str:
    """构建单条 Spider 的推送消息正文（Markdown 格式）。

    Args:
        spider_name: Spider 名称
        new_count: 新增条目数
        changed_count: 变化的条目数
        sample_items: 新增/变化的样例条目
        keywords: 命中的关键词
    """
    lines = [
        f"## 🕵️ {spider_name}",
        "",
        f"- **新增条目**: {new_count}",
        f"- **变化条目**: {changed_count}",
    ]

    if keywords:
        lines.append(f"- **命中关键词**: {', '.join(keywords)}")

    if sample_items:
        lines.append("")
        lines.append("### 📋 样例")
        lines.append("")

        for i, item in enumerate(sample_items[:5], 1):
            name = item.get("name", f"条目 #{i}")
            url = item.get("url", "")
            lines.append(f"**{i}. {name}**")
            if url:
                lines.append(f"[{url}]({url})")
            lines.append("")

    return "\n".join(lines)
