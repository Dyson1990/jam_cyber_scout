# jam_cyber_scout

定时自动爬取 → 分析 → 微信推送的安全情报（可定制）机器人。

---

## 🏗 架构总览

```
┌──────────────────────────────────────────────────┐
│  GitHub Actions (每天北京时间 9:00 / 手动触发)     │
│                                                    │
│  ┌─────────────────────┐                           │
│  │ jam_eden_crawler     │ ← 独立仓库，Scrapy 爬虫   │
│  │ Dyson1990/jam_eden_crawler                       │
│  │ ├─ spiders/xxx.py   │                           │
│  │ ├─ pipelines.py     │ → 写入 data.db            │
│  │ └─ ...              │                           │
│  └──────────┬──────────┘                           │
│             │ data.db                               │
│             ▼                                      │
│  ┌─────────────────────┐                           │
│  │ jam_cyber_scout      │ ← 本项目                  │
│  │ ├─ main.py          │   读 DB → 对比变化         │
│  │ ├─ notifier.py      │   调用 PushPlus API       │
│  │ └─ state.py         │   状态持久化 (Cache)       │
│  └──────────┬──────────┘                           │
│             │                                      │
│             ▼                                      │
│  ┌─────────────────────┐                           │
│  │ PushPlus 推送加      │                           │
│  │ → 你的微信            │                           │
│  └─────────────────────┘                           │
└──────────────────────────────────────────────────┘
```

**两个仓库完全独立**：
- [`jam_eden_crawler`](https://github.com/Dyson1990/jam_eden_crawler) — 纯爬虫。可以独立开发、测试、更新 Spider，不影响本项目的推送逻辑
- `jam_cyber_scout`（本项目）— 调度 + 分析 + 推送。不关心爬虫内部实现，只读 `data.db` 的结果

---

## 🚀 快速开始

### 前置条件

1. **PushPlus Token** — 扫码关注 [PushPlus 推送加](https://www.pushplus.plus) 公众号，获取你的 token
2. **Eden Crawler** — 确保仓库 `Dyson1990/jam_eden_crawler` 中有可运行的 spider

### 第一步：配置 GitHub Secrets

1. 打开本仓库 → **Settings** → **Secrets and variables** → **Actions**
2. 点击 **New repository secret**
3. Name: `PUSHPLUS_TOKEN`
4. Value: 你在 PushPlus 获取的 token

### 第二步：添加爬虫目标

在 [`jam_eden_crawler`](https://github.com/Dyson1990/jam_eden_crawler) 仓库中创建一个新的 Spider 文件。例如：

```python
# eden_crawler/spiders/freebuf.py
import scrapy
from eden_crawler.items import DynamicItem

class FreeBufSpider(scrapy.Spider):
    name = "freebuf"
    start_urls = ["https://www.freebuf.com/"]

    custom_settings = {"PROXY_ENABLED": False}  # 关闭本地代理

    def parse(self, response):
        for article in response.css("div.article-item"):
            item = DynamicItem()
            item["name"] = article.css("a.title::text").get()
            item["url"] = article.css("a.title::attr(href)").get()
            item["summary"] = article.css("p.summary::text").get()
            yield item
```

### 第三步：修改 workflow

编辑 `.github/workflows/scout.yml`，把第 5 步的 spider 运行命令改为你的 spider：

```yaml
- name: Run Eden Crawler spiders
  run: |
    cd eden_crawler
    scrapy crawl freebuf
    # 如果有多个 spider，可以运行多行:
    # scrapy crawl cert_news
    # scrapy crawl vul_report
```

### 第四步：推送代码，触发运行

```bash
git add .
git commit -m "feat: add scout workflow"
git push
```

之后每天北京时间 9:00 自动运行。也可以到 Actions 页面手动触发测试。

---

## 📁 文件说明

| 文件 | 职责 |
|---|---|
| `.github/workflows/scout.yml` | GitHub Actions 定时/手动触发编排 |
| `main.py` | 主逻辑：读取 data.db → 对比上次状态 → 调用推送 |
| `config.py` | 所有可配置参数（Token 走环境变量） |
| `notifier.py` | PushPlus API 封装 + 消息构建 |
| `state.py` | 状态持久化（通过 GitHub Cache 实现跨运行记忆） |
| `requirements.txt` | 本项目依赖（极简，仅 requests） |

---

## 🔧 本地测试

```bash
# 1. Clone Eden Crawler 到本地
git clone git@github.com:Dyson1990/jam_eden_crawler.git eden_crawler

# 2. 设置环境变量
# Windows:
set PUSHPLUS_TOKEN=your_token_here
# Mac/Linux:
export PUSHPLUS_TOKEN=your_token_here

# 3. 安装依赖
pip install -r eden_crawler/requirements.txt
pip install -r requirements.txt

# 4. 先运行爬虫
cd eden_crawler
scrapy crawl your_spider_name
cd ..

# 5. 再运行分析 + 推送
python main.py
```

---

## 🔄 Eden Crawler 如何独立更新

Eden Crawler 和本项目的更新完全解耦：

| 场景 | 操作 |
|---|---|
| **新增/修改 Spider** | 在 Eden Crawler 仓库直接提交，不需要动本项目 |
| **升级 Scrapy / 依赖** | 在 Eden Crawler 仓库改 `requirements.txt`，下轮 workflow 自动安装新版 |
| **修改调度时间** | 改本项目 `.github/workflows/scout.yml` 里的 cron |
| **修改推送逻辑** | 改本项目 `main.py` / `notifier.py`，不影响爬虫 |

---

## 📊 状态持久化原理

```
第 N 次运行:
  restore cache → state.json (第 N-1 次的结果)
  ↓
  scrapy crawl → data.db (本次最新数据)
  ↓
  main.py: 对比 hash → 有变化 → PushPlus 推送
  ↓
  save cache → state.json (本次结果，供下次使用)

Cache 未命中 (首次运行 / 超过 7 天):
  → 当作首次运行，全部推送一次，之后恢复正常
```

---

## 🛠 自定义关键词

编辑 `config.py` 中的 `KEYWORDS` 列表：

```python
KEYWORDS = [
    "你的关键词", "CVE", "RCE", ...
]
```

关键词命中后会在推送标题中标注，帮助快速筛选重要信息。

---

## 📝 注意事项

- GitHub Actions 免费额度：每月 2000 分钟（私有仓库），公开仓库无限
- PushPlus 免费版：每日 200 条推送限制（远远够用）
- Cache 存储上限 10GB，7 天未命中会自动清理
- 如果想修改执行频率，编辑 `scout.yml` 中的 `cron` 表达式即可
