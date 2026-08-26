# Cyber Scout

运行在 GitHub Actions 上的定时任务框架。采用 AppFlow 流水线：每个 App 从 stdin 读 JSONL，处理后写 JSONL 到 stdout，前一个 App 的输出管道接入下一个 App 的输入，由 `.github/workflows/scout.yml` 触发执行。

## 如何写一个 App

1. 建目录 `apps/<name>/`，放 `__init__.py`（可空）和 `entry.py`。
2. `entry.py` 是唯一入口，被 `python -m apps.<name>.entry <args>` 调用。
3. 在 `config.py` 的 `jobs` 里把 App 加进流水线。

最小 App：

```python
# apps/<name>/entry.py
import json, sys

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        # 处理...
        print(json.dumps(item, ensure_ascii=False))
        sys.stdout.flush()

if __name__ == "__main__":
    main()
```

## 约定

- **数据契约**：stdin/stdout 都是 JSONL，每行一个 JSON。第一个 App 无 stdin，后续 App 消费上一级输出。
- **args 只传配置**，不传业务数据；业务数据走 stdin。
- 子进程统一用 `sys.executable` 启动（如 `[sys.executable, "-m", ...]`），保证 venv 兼容。
- 日志写 `stderr`，数据写 `stdout`，避免污染管道。
- 敏感信息（如 token）通过 GitHub Actions secrets 注入，不硬编码。

## 结构

```
main.py                 # CLI 入口，读取 config.py 并运行流水线
config.py               # jobs 定义：{job名: [(app名, [args...]), ...]}
appflow/                # Pipeline / AppProcess 核心（无需改动）
apps/<name>/entry.py    # 各 App 入口
.github/workflows/      # GitHub Actions 定时触发配置
```

## 运行

```bash
python main.py            # 列出所有 job
python main.py <job名>    # 运行指定 job
```
