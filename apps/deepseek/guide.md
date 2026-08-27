# deepseek

逐条读输入，调 DeepSeek 生成一句话总结，追加 `reply` 字段输出。

## 输入
JSONL，每行一个对象；取 `prompt` / `text` 字段作提问，缺省总结整条。
作为首个 App（无 stdin）时，用 args 拼成提问。

## 输出
输入对象 + `reply` 字段（总结文本）。

## 环境变量
DEEPSEEK_API_KEY
