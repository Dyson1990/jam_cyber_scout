# plant_keeper

植物浇水业务，维护 `plants.json` 状态。三个阶段用 args 区分：

- `remind`: 输出提醒请求 `{op:"send",ref,chat_id,text}`
- `check`: 输出确认请求 `{op:"check",ref,message_id}`
- `apply`: 读 feishu 结果 `{op:"sent"|"checked",...}`，回写状态；无输出
