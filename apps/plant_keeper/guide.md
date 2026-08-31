# plant_keeper

植物养护业务，所有状态集中在 `state.json`。阶段用 args 区分：

- `plan`: 汇总植物/肥料/浇水器信息生成询问 AI 的 prompt，输出 `{prompt}`
- `apply_plan`: 读 deepseek 返回的计划 JSON，回写 `state.json`；无输出
- `remind`: 输出提醒请求 `{op:"send",ref,chat_id,text}`（浇水/施肥/调参）
- `check`: 输出确认请求 `{op:"check",ref,message_id}`
- `apply`: 读 feishu 结果 `{op:"sent"|"checked",...}`，回写状态；无输出

## 状态文件 `state.json`
- `plants`: 植物数组，每株内联 `name`/`location`/`cultivation`（培育方式）/`water_ml`（半水培换水量）/`interval_days`/`fertilize_interval_days` 及 `next_water`/`next_fertilize`（AI 排期）、`fertilizer_use`、`care_note`（近期注意事项）、`auto_water`
- `buy_fertilizer`: 待购肥料清单
- `device`: 浇水器当前参数 + AI 建议参数 + 确认状态
- `fertilizers`: 肥料库存，`record_type` 为 `barcode` 或 `name`
- `feishu_chat_id`: 提醒目标群
