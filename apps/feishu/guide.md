# feishu

飞书通信。两种模式，由环境变量 `FEISHU_WEBHOOK` 决定：
- 设置了 webhook → 读 `{title, content}` 发群机器人消息。
- 否则走自建应用 API，读 `{op,...}` 请求。

## webhook 模式
输入: `{title, content}`；输出: 无

## 自建应用模式
输入: `{op:"send",ref,chat_id,text}` 或 `{op:"check",ref,message_id}`
输出: `{op:"sent",ref,message_id}` 或 `{op:"checked",ref,reacted,action_time}`

## 环境变量
`FEISHU_WEBHOOK`（webhook 地址）、`FEISHU_APP_ID` / `FEISHU_APP_SECRET`（自建应用）
