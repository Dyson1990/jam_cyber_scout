import requests

def send_wechat(msg):
    token = 'f14fa661a6694c0f9fad82cd4ebe920e'#前边复制到那个token
    title = 'title1'
    content = msg
    template = 'html'
    url = f"https://www.pushplus.plus/send?token={token}&title={title}&content={content}&template={template}"
    print(url)
    r = requests.get(url=url)
    print(r.text)

if __name__ == '__main__':
    msg = 'this is a  python test'
    send_wechat(msg)