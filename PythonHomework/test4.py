import requests

BAIDU_API_KEY = "9YSronlqcRAPBNQgZYwAt3ry"
BAIDU_SECRET_KEY = "A7ETaTeRMsFsJJ1IsrW1rBPzUfRqXqcN"

def test_token():
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": BAIDU_API_KEY,
        "client_secret": BAIDU_SECRET_KEY
    }
    resp = requests.post(url, params=params)
    print("接口返回完整内容：", resp.json())

if __name__ == "__main__":
    test_token()