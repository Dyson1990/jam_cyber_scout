"""req_sync 业务流：扫描 GitHub 提交，命中 REQ-xxx 的需求标「已完成」回写飞书。"""

# 业务参数：需求管理多维表格 app token
FEISHU_REQ_APP_TOKEN = "MexobZ2eHaZelzsdKlDc2NCFnyh"

STAGES = [
    ("req_sync", [FEISHU_REQ_APP_TOKEN], None),  # 终结点：无 stdin，扫描并回写，仅副作用
]
