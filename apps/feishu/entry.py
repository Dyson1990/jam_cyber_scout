"""飞书 App 入口 — 消息委托给 feishu.py，多维表格同步委托给 bitable.py。"""

import sys

from apps.feishu.feishu import main as feishu_main

# Windows 控制台默认 GBK，强制 UTF-8 避免中文/emoji 输出报错
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def main() -> int:
    if "bitable" in sys.argv:
        from apps.feishu import bitable
        return bitable.main()
    return feishu_main()


if __name__ == "__main__":
    sys.exit(main())
