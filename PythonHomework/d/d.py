import requests
import time

# 目标网址
URL = "https://p.xtrvi.cn/?promo=XPMG8FG.com"

def visit_website():
    try:
        resp = requests.get(URL, timeout=10)
        print(f"✅ 访问成功 | 状态码：{resp.status_code} | {time.ctime()}")
    except Exception as e:
        print(f"❌ 访问失败：{str(e)} | {time.ctime()}")


if __name__ == "__main__":
    print("程序启动，每5秒访问一次网站，按 Ctrl+C 停止\n")
    while True:
        visit_website()
        time.sleep(5)  # 等待5秒