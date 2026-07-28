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
from typing import Any

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

    - 通过 stdin 将输入 JSONL 喂给子进程
    - 从 stdout 逐行收集 JSONL 输出
    - 监控 exit code 判定成功/失败
    """

    def __init__(self, cmd: list[str]):
        """
        Args:
            cmd: 启动 App 的命令行，例如 ["python", "scrapy_app/main.py", "movie"]
        """
        self.cmd = cmd
        self.returncode: int | None = None

    async def run(self, input_data: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """启动子进程，传入数据，返回收集的 JSONL 输出。

        Args:
            input_data: 要传入 stdin 的 JSONL 数据，None 表示无输入

        Returns:
            子进程 stdout 产出的 JSONL 数据列表
        """
        stdin_arg = asyncio.subprocess.PIPE if input_data else None

        env = _build_env()

        proc = await asyncio.create_subprocess_exec(
            *self.cmd,
            stdin=stdin_arg,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        # 并行处理：喂 stdin + 读 stdout + 读 stderr
        async def feed_stdin() -> None:
            if proc.stdin and input_data:
                text = "\n".join(
                    json.dumps(item, ensure_ascii=False) for item in input_data
                ) + "\n"
                proc.stdin.write(text.encode("utf-8"))
                await proc.stdin.drain()
                proc.stdin.close()

        async def read_stdout() -> list[dict[str, Any]]:
            items: list[dict[str, Any]] = []
            if proc.stdout:
                async for line in proc.stdout:
                    line = line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning(f"[{self.cmd[0]}] 跳过无效 JSONL: {line[:80]}")
            return items

        async def read_stderr() -> str:
            if proc.stderr:
                data = await proc.stderr.read()
                return data.decode("utf-8", errors="replace")
            return ""

        results = await asyncio.gather(
            feed_stdin(),
            read_stdout(),
            read_stderr(),
            proc.wait(),
        )

        self.returncode = results[3]
        output: list[dict[str, Any]] = results[1]
        stderr_text: str = results[2]

        if stderr_text:
            app_tag = self.cmd[-1] if len(self.cmd) > 1 else self.cmd[0]
            for line in stderr_text.strip().split("\n"):
                logger.info(f"[{app_tag}] {line}")

        if self.returncode != 0:
            raise RuntimeError(
                f"App '{' '.join(self.cmd)}' 退出码: {self.returncode}\nstderr: {stderr_text[:500]}"
            )

        return output
