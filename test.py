# encoding:utf-8
import requests
import json
token = '59f91ad736064d97a453528d9ccfdeca' #在pushpush网站中可以找到
title= '标题' #改成你要的标题内容
content ='内容' #改成你要的正文内容
url = 'http://www.pushplus.plus/send'
data = {
    "token":token,
    "title":title,
    "content":content
}
body=json.dumps(data).encode(encoding='utf-8')
headers = {'Content-Type':'application/json'}
resp = requests.post(url,data=body,headers=headers,timeout=15)
print(resp.status_code)