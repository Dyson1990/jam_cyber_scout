"""
jam_cyber_scout 配置
====================
- 敏感信息（Token）走环境变量，不在代码里硬编码
- 其他可调参数集中在这里，方便修改
"""

import os

# ============================================================
# PushPlus 配置
# 在 GitHub Secrets 里设置 PUSHPLUS_TOKEN，本地测试设环境变量
# PushPlus 官网: https://www.pushplus.plus
# ============================================================
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")

# ============================================================
# Eden Crawler 相关
# ============================================================
# Eden Crawler 在本 workflow 中的 checkout 路径
EDEN_CRAWLER_DIR = "eden_crawler"

# Eden Crawler 的 SQLite 数据库路径（相对于 EDEN_CRAWLER_DIR）
EDEN_DB_PATH = "data.db"

# 要检查的 spider 名称列表 — 只检查这些 spider 对应的表
# 如果不指定（空列表），则检查 data.db 中所有 spider_* 表
SPIDER_NAMES = []  # 例如: ["security_news", "vul_report"]

# ============================================================
# 分析配置
# ============================================================
# 关键词列表 — 命中时在推送消息中高亮
KEYWORDS = [
    "漏洞", "CVE", "0day", "RCE", "提权", "后门", "勒索",
    "数据泄露", "APT", "木马", "恶意软件", "补丁", "高危",
    "远程代码执行", "SQL注入", "XSS", "CSRF", "权限提升",
]

# 推送时展示的最大新增/变更数量（避免消息过长）
MAX_ALERT_ITEMS = 20

# ============================================================
# 状态文件路径（由 GitHub Actions Cache 持久化）
# ============================================================
STATE_FILE = "state.json"
