# report

整理运行反馈。读运行摘要，生成简短消息。

## 输入
RunSummaryItem: `{job, status, count, stages}`（stages 为 `[{stage,status,count,error}]`）

## 输出
ReportItem: `{title, content}`（成功简短 / 失败完整展示错误）
