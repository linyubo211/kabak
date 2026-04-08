import os
import re
import requests
import time
import base64

# --- 配置区 ---
# 从环境变量获取 Cookie，保护账号安全
FOFA_COOKIE = os.getenv("FOFA_COOKIE")
TARGET_FILE = "py/1000_alive.txt"
CHECK_PATH = "/iptv/live/1000.json?key=txipt"

# 搜索关键词："/iptv/live" && country="CN"
# 增加 order=last_updatetime 确保获取的是最新收录的
QUERY = '"/iptv/live" && country="CN"'
QBASE64 = base64.b64encode(QUERY.encode()).decode()
SEARCH_URL = f"https://fofa.info/result?qbase64={QBASE64}&order=last_updatetime"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Cookie": FOFA_COOKIE,
    "Referer": "https://fofa.info/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,/ ;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9"
}

def crawl_fofa():
    if not FOFA_COOKIE:
        print("❌ 错误：未检测到 FOFA_COOKIE，请在 GitHub Secrets 中配置")
        return

    print(f"📡 正在通过 Web 页面检索最新资产...")
    try:
        response = requests.get(SEARCH_URL, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            html = response.text
            # 提取页面中的 IP:PORT 格式
            # 匹配类似 1.2.3.4:8080 的字符串
            raw_hosts = re.findall(r'((?:\d{1,3}\.){3}\d{1,3}:\d+)', html)
            # 去重
            unique_hosts = list(set(raw_hosts))
            print(f"✅ 成功从页面提取到 {len(unique_hosts)} 个唯一主机地址")
            return unique_hosts
        elif response.status_code == 403:
            print("❌ 403 被拒：可能是 Cookie 失效或触发了人机验证")
        else:
            print(f"❌ 请求失败，状态码：{response.status_code}")
    except Exception as e:
        print(f"❌ 运行异常：{e}")
    return []

def main():
    hosts = crawl_fofa()
    if not hosts:
        return

    # 确保目录存在
    os.makedirs(os.path.dirname(TARGET_FILE), exist_ok=True)
    
    # 读取现有文件内容
    existing_urls = set()
    if os.path.exists(TARGET_FILE):
        with open(TARGET_FILE, "r", encoding="utf-8") as f:
            existing_urls = {line.strip() for line in f if line.strip()}

    new_count = 0
    with open(TARGET_FILE, "a", encoding="utf-8") as f:
        for host in hosts:
            # 拼接完整链接
            full_url = f"http://{host}{CHECK_PATH}"
            if full_url not in existing_urls:
                f.write(full_url + "\n")
                existing_urls.add(full_url)
                new_count += 1

    print("-" * 30)
    print(f"📊 任务总结：")
    print(f"🔹 本次抓取：{len(hosts)} 个")
    print(f"🔹 新增记录：{new_count} 条")
    print(f"🔹 文件总数：{len(existing_urls)} 条")
    print("-" * 30)

if __name__ == "__main__":
    main()
