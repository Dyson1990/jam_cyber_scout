# eden_crawler

爬虫入口，启动 Scrapy 抓取数据，结果以 JSONL 输出。

## 输入
无（首个 App），或上游传入的种子数据 `{"url": "..."}`（可选）。

## 输出
爬取结果，每行一个 JSON 对象，字段随 spider 而定：
- `ip`: `ip`(必填) / `country` / `region` / `city` / `org`
- `car`: `level` / `name` / `url` / `brand` / `series` / `price` / `specs` / `images` / `...`（动态字段）

## args
`<spider>` — 爬虫名（`ip` / `car`）
