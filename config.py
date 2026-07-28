"""
业务流配置
==========
在这里定义你的 Job。每个 Job 是一组按顺序执行的 App。

格式:
    jobs = {
        "job名称": [
            ("app名称", ["参数1", "参数2", ...]),
            ...
        ],
    }

运行:
    python main.py <job名称>
    python main.py              # 列出所有 Job
"""

jobs = {
    "movie_scout": [
        ("scrapy_app", ["movie"]),
        ("analyzer_app", []),
        ("pushplus", []),
    ],
    "news_scout": [
        ("scrapy_app", ["news"]),
        ("analyzer_app", []),
        ("pushplus", []),
    ],
    "car_crawl": [
        ("eden_crawler", ["car"]),
        ("pushplus", []),
    ],
    "ip_crawl": [
        ("eden_crawler", ["ip"]),
        ("pushplus", []),
    ],
    "ip_test_crawl": [
        ("eden_crawler", ["ip_test"]),
        ("pushplus", []),
    ],
}
