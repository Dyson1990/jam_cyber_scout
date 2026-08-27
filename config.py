"""全局配置
==========
测试环境开关与飞书反馈 webhook。业务流定义见 jobs/ 目录。
"""

# 测试环境开关：为 True 时，每个 job 末尾自动追加 report + feishu
TEST_MODE = True

# 测试反馈用的飞书群机器人 webhook
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/075d015c-20f1-4932-b625-dc629db6b02a"
