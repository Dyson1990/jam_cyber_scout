# req_sync

扫描 GitHub 提交日志，命中 `REQ-xxx` 编号的需求自动标「已完成」回写飞书多维表格。

## 输入
无（首个 App，自行读取飞书表 + GitHub API）。

## 输出
无数据输出；判定摘要写 stderr（日志）。

## 飞书表字段
Requirements 表：`status` / `req_id` / `repo` / `branch` / `updated_at` / `title`。

## args
<需求表 app_token>（由 job 传入）

## 环境变量
FEISHU_BITABLE_APP_ID / FEISHU_BITABLE_APP_SECRET（多维表格企业应用，与盆栽共用）、GITHUB_TOKEN（可选，Actions 自动注入）
