# Cyber Scout

运行在 GitHub Actions 上的定时任务框架。采用 AppFlow 流水线：App 间通过 **Item**（严格校验的 JSONL 数据单元）传递数据，由 `.github/workflows/scout.yml` 触发执行。

## 核心概念

- **Item**：App 间传输的数据单元。子类用 dataclass 字段注解声明结构，反序列化时严格校验，非法输入直接抛 `ItemValidationError`。
- **Job**：一组按顺序执行的 App，定义在 `jobs/` 下，一个 job 一个文件，同时定义该 job 内流转的 Item 类型。
- **App**：一个子进程，从 stdin 读 JSONL，处理后写 JSONL 到 stdout。

## 业务流执行

```
识别 job → 运行 app1 → 获得输出 → 转为 Item(严格校验) → 运行 app2(传 Item) → ... → 最后一个
```

每阶段输出经该阶段声明的 `item_cls.loads()` 严格校验，非法直接报错并中断，不会静默跳过。

## 新建一个 App（完整闭环）

新建 App 要同时做三件事，字段必须一一对应。

### 1. 写 `apps/<name>/entry.py`

唯一入口，被 `python -m apps.<name>.entry <args>` 调用。内部固定三步：**解析输入 → 主流程 → 输出**。

```python
# apps/<name>/entry.py
import json, os, sys

def main():
    # 配置走 args 或环境变量，业务数据走 stdin
    tag = sys.argv[1] if len(sys.argv) > 1 else "default"
    token = os.getenv("SOME_TOKEN", "")

    # 首个 App 无 stdin 输入（需自己产出数据）；其余 App 逐行读上一级输出
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)                          # 1. 解析输入

        result = {"title": item.get("title", ""), "tag": tag}  # 2. 主流程

        print(json.dumps(result, ensure_ascii=False))    # 3. 输出（字段必须匹配 job 声明的 Item）
        sys.stdout.flush()

if __name__ == "__main__":
    main()
```

### 2. 写 `apps/<name>/guide.md`

说明该 App 的输入、输出、args、环境变量，供下次快速接入。

```markdown
# <name>

## 输入
{title: str}

## 输出
{title: str, tag: str}

## args
<tag>（可选，配置项）

## 环境变量
SOME_TOKEN
```

### 3. 在 `jobs/` 注册

`appflow/item.py` 提供 `Item` 基类；job 文件定义流转的 Item 子类和 `STAGES`。

```python
# jobs/<job>.py
from dataclasses import dataclass
from appflow.item import Item

@dataclass
class OutItem(Item):
    title: str          # 无默认值 = 必填
    tag: str = ""       # 有默认值 = 可选

# (app名, args, 该阶段输出的 Item 类型；终结点为 None)
STAGES = [
    ("<name>", ["my_tag"], OutItem),   # app 名对应 apps/<name>/ 目录
]
```

**关键：`entry.py` 输出的每个字段，必须能被 `STAGES` 里声明的 `item_cls` 校验通过**——字段名、必填、类型一致，否则该阶段直接报错中断。上一阶段声明的输出 Item 类型，就是下一阶段的输入。

- 首个 App 无 stdin（自行产出数据），其余 App 从 stdin 读上一阶段输出。
- 终结点（`None`）不校验输出，仅执行副作用（发消息/回写状态）。

## 约定

- **数据契约**：App 间用 Item（JSONL 每行一个对象）传数据。
- **严格校验**：非对象 / 缺必填 / 类型不符 / 未知字段 → 报错；子类 `allow_unknown = True` 可放行未知字段（如爬虫动态字段）。
- **args 只传配置**，不传业务数据；业务数据走 stdin；敏感信息（token）走环境变量 / GitHub Actions secrets。
- 子进程统一 `sys.executable -m` 启动，保证 venv 兼容。
- 日志写 `stderr`，数据写 `stdout`，避免污染管道。
- Apps 之间不能相互影响，功能重复。

## 结构

```
main.py                 # CLI 入口，从 jobs/ 加载并运行流水线
jobs/<job>.py           # 每个 job：定义流转的 Item 类型 + STAGES
appflow/                # Item / Pipeline / AppProcess 核心
apps/<name>/entry.py    # 各 App 入口
apps/<name>/guide.md    # 该 App 的输入/输出说明
.github/workflows/      # GitHub Actions 定时触发
```

## 运行

```bash
python main.py            # 列出所有 job
python main.py <job名>    # 运行指定 job
```
