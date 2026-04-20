# -*- coding: utf-8 -*-
import yaml
import urllib.parse
import base64
import json
import os

def parse_trojan_url(url):
    try:
        if not url.startswith("trojan://"):
            return None
        url = url[len("trojan://"):]
        if "#" in url:
            url, name = url.split("#", 1)
            name = urllib.parse.unquote(name)
        else:
            name = "Trojan节点"

        userinfo, hostport = url.split("@", 1)
        password = userinfo
        host_port_part, query_part = hostport.split("?", 1)
        query = urllib.parse.parse_qs(query_part)
        server, port = host_port_part.split(":", 1)
        port = int(port)

        return {
            "type": "trojan",
            "name": name,
            "server": server,
            "port": port,
            "password": password,
            "sni": query.get("sni", [None])[0],
            "ws_path": query.get("path", [None])[0],
            "ws_host": query.get("host", [None])[0]
        }
    except:
        return None

def parse_vmess_url(url):
    try:
        if not url.startswith("vmess://"):
            return None
        data = url[len("vmess://"):]
        data += "=" * ((4 - len(data) % 4) % 4)
        decoded = base64.b64decode(data).decode("utf-8")
        js = json.loads(decoded)
        return {
            "type": "vmess",
            "name": js.get("ps", "VMess节点"),
            "server": js.get("add"),
            "port": int(js.get("port", 443)),
            "uuid": js.get("id"),
            "aid": js.get("aid", 0),
            "sni": js.get("sni", ""),
            "host": js.get("host", ""),
            "path": js.get("path", "/"),
            "tls": js.get("tls", ""),
            "net": js.get("net", "ws")
        }
    except:
        return None

# ==================== 自动查找 nodes.txt ====================
current_dir = os.path.dirname(os.path.abspath(__file__))
txt_path = os.path.join(current_dir, "nodes.txt")

print(f"📂 当前目录：{current_dir}")
print(f"📄 寻找节点文件：{txt_path}")

if not os.path.exists(txt_path):
    print("\n❌ 错误：没找到 nodes.txt 文件！")
    print("请把 nodes.txt 放在这个目录里：" + current_dir)
    input("按回车退出...")
    exit()

# 读取节点
nodes = []
with open(txt_path, "r", encoding="utf-8") as f:
    lines = [l.strip() for l in f if l.strip()]

print(f"✅ 找到 {len(lines)} 行链接")

for line in lines:
    node = parse_trojan_url(line) or parse_vmess_url(line)
    if node:
        nodes.append(node)

if not nodes:
    print("❌ 没有解析出任何有效节点")
    input("按回车退出...")
    exit()

# 生成配置
proxies = []
for node in nodes:
    if node["type"] == "trojan":
        proxies.append({
            "name": node["name"],
            "type": "trojan",
            "server": node["server"],
            "port": node["port"],
            "password": node["password"],
            "sni": node["sni"],
            "skip-cert-verify": True,
            "network": "ws",
            "ws-path": node["ws_path"],
            "ws-headers": {"Host": node["ws_host"]},
            "udp": True
        })
    elif node["type"] == "vmess":
        proxies.append({
            "name": node["name"],
            "type": "vmess",
            "server": node["server"],
            "port": node["port"],
            "uuid": node["uuid"],
            "alterId": node["aid"],
            "cipher": "auto",
            "tls": node["tls"] == "tls",
            "skip-cert-verify": True,
            "network": node["net"],
            "ws-path": node["path"],
            "ws-headers": {"Host": node["host"]},
            "sni": node["sni"],
            "udp": True
        })

proxy_groups = [{"name": "代理", "type": "select", "proxies": [p["name"] for p in proxies] + ["DIRECT"]}]
rules = ["GEOIP,CN,DIRECT", "MATCH,代理"]
config = {"proxies": proxies, "proxy-groups": proxy_groups, "rules": rules}

# 输出 yaml
out_path = os.path.join(current_dir, "output.yaml")
with open(out_path, "w", encoding="utf-8") as f:
    yaml.dump(config, f, allow_unicode=True, sort_keys=False)

print(f"\n🎉 成功生成！共 {len(nodes)} 个节点")
print(f"📄 输出文件：{out_path}")
input("按回车退出程序...")