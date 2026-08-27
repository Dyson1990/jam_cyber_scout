"""
子进程管理
=========
负责启动 App 子进程，通过 stdin 喂数据，从 stdout 收集输出。
"""

import asyncio
import json
import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)


_win_env_cache: dict[str, str] | None = None


def _build_env() -> dict[str, str]:
    """构建子进程环境变量。

    在 Windows 上，Git Bash / msys2 不会继承系统环境变量，需要手动从注册表读取。
    GitHub Actions 中 secrets 通过 workflow env: 注入，已包含在 os.environ 中，不受影响。
    """
    global _win_env_cache

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # 关闭子进程输出缓冲，崩溃时日志不丢失
    env["PYTHONUNBUFFERED"] = "1"

    if sys.platform == "win32":
        if _win_env_cache is None:
            try:
                result = subprocess.run(
                    ["powershell.exe", "-Command",
                     "[Environment]::GetEnvironmentVariables('User') | ConvertTo-Json"],
                    capture_output=True, timeout=5,
                )
                if result.returncode == 0:
                    _win_env_cache = json.loads(result.stdout)
                else:
                    _win_env_cache = {}
            except Exception:
                _win_env_cache = {}

        for k, v in _win_env_cache.items():
            if k not in env and isinstance(v, str):
                env[k] = v

    return env


class AppProcess:
    """封装一个 App 子进程的完整生命周期。

    - 通过 stdin 将输入 Item 序列化为 JSONL 喂给子进程
    - 从 stdout 逐行收集原始 JSONL 字符串（Item 校验交给 Pipeline）
    - 监控 exit code 判定成功/失败
    """

    def __init__(self, cmd: list[str]):
        self.cmd = cmd
        self.returncode: int | None = None

    async def run(self, input_items: list | None = None) -> list[str]:
        """启动子进程，传入数据，返回 stdout 原始 JSONL 行列表。

        Args:
            input_items: 要传入的 Item 列表（有 dumps() 方法），None 表示无输入

        Returns:
            子进程 stdout 产出的原始行列表（去空白、去空行，不解析）
        """
        stdin_arg = asyncio.subprocess.PIPE if input_items else None

        env = _build_env()

        proc = await asyncio.create_subprocess_exec(
            *self.cmd,
            stdin=stdin_arg,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        app_tag = self.cmd[-1] if len(self.cmd) > 1 else self.cmd[0]

        async def feed_stdin() -> None:
            if proc.stdin and input_items:
                text = "\n".join(
                    (item.dumps() if hasattr(item, "dumps")
                     else json.dumps(item, ensure_ascii=False))
                    for item in input_items
                ) + "\n"
                proc.stdin.write(text.encode("utf-8"))
                await proc.stdin.drain()
                proc.stdin.close()

        async def read_stdout() -> list[str]:
            lines: list[str] = []
            if proc.stdout:
                async for line in proc.stdout:
                    line = line.decode("utf-8", errors="replace").strip()
                    if line:
                        lines.append(line)
            return lines

        async def read_stderr() -> str:
            lines: list[str] = []
            if proc.stderr:
                async for line in proc.stderr:
                    text = line.decode("utf-8", errors="replace").rstrip()
                    if text:
                        logger.info(f"[{app_tag}] {text}")
                        lines.append(text)
            return "\n".join(lines)

        results = await asyncio.gather(
            feed_stdin(),
            read_stdout(),
            read_stderr(),
            proc.wait(),
        )

        self.returncode = results[3]
        output: list[str] = results[1]
        stderr_text: str = results[2]

        if self.returncode != 0:
            raise RuntimeError(
                f"App '{' '.join(self.cmd)}' 退出码: {self.returncode}\n--- stderr ---\n{stderr_text}"
            )

        return output
