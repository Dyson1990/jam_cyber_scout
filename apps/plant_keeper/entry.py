"""植物养护业务 App 入口 — 按 args 分发到各阶段。

阶段（实现分散在 plan.py / remind.py / update.py）:
    plan / apply_plan    AI 规划养护计划
    remind               生成提醒请求
    check / apply        确认并回写状态
"""

import sys

from apps.plant_keeper import plan, remind, update

# Windows 控制台默认 GBK，强制 UTF-8 避免中文/emoji 输出报错
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

_OPS = {
    "plan": plan.plan,
    "apply_plan": plan.apply_plan,
    "remind": remind.remind,
    "check": update.check,
    "apply": update.apply,
}


def main() -> int:
    for name, fn in _OPS.items():
        if name in sys.argv:
            return fn()
    print("用法: python -m apps.plant_keeper.entry [plan|apply_plan|remind|check|apply]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
