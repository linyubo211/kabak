import os
import re
import requests
import time
import base64
import random

# --- 配置区 ---
FOFA_COOKIE = os.getenv("FOFA_COOKIE")
TARGET_FILE = "py/1000_alive.txt"
CHECK_PATH = "/iptv/live/1000.json?key=txipt"

# 搜索关键词
QUERY = '"/iptv/live" && country="CN"'
QBASE64 = base64.b64encode(QUERY.encode()).decode()
SEARCH_URL = f"https://fofa.info/result?qbase64={QBASE64}&order=last_updatetime"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Cookie": FOFA_COOKIE,
    "Referer": "https://fofa.info/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive"
}

def keep_session_alive(session):
    """
    模拟人类行为：在抓取前先随机访问几个页面，以此激活并维持 Cookie 有效性
    """
    active_urls = [
        "https://fofa.info/",
        "https://fofa.info/personal/center",
        "https://fofa.info/library",
        "https://fofa.info/about"
    ]
    # 随机选 1-2 个页面访问
    targets = random.sample(active_urls, k=random.randint(1, 2))
    
    print("🔄 正在执行 Session 活跃维护...")
    for url in targets:
        try:
            # 模拟随机停顿
            time.sleep(random.uniform(2, 5))
            resp = session.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                print(f"✅ 成功模拟访问：{url}")
            else:
                print(f"⚠️ 模拟访问 {url} 返回状态码：{resp.status_code}")
        except Exception as e:
            print(f"❌ 活跃维护尝试失败：{e}")

def crawl_fofa():
    if not FOFA_COOKIE:
        print("❌ 错误：未检测到 FOFA_COOKIE")
        return []

    # 使用 session 管理 Cookie，可以自动处理服务器返回的 Set-Cookie 更新
    with requests.Session() as session:
        # 第一步：先维持活跃
        keep_session_alive(session)
        
        # 模拟进入搜索页前的停顿
        time.sleep(random.uniform(3, 6))
        
        print(f"📡 正在检索最新资产...")
        try:
            response = session.get(SEARCH_URL, headers=HEADERS, timeout=30)
            if response.status_code == 200:
                html = response.text
                raw_hosts = re.findall(r'((?:\d{1,3}\.){3}\d{1,3}:\d+)', html)
                unique_hosts = list(set(raw_hosts))
                
                # 如果没抓到 IP 但页面能打开，可能是被反爬或者没登录
                if not unique_hosts and "登录" in html:
                    print("❌ 警告：页面提示需要登录，Cookie 可能已失效！")
                
                return unique_hosts
            elif response.status_code == 403:
                print("❌ 403 被拒：触发人机验证或账号受限")
            else:
                print(f"❌ 请求失败，码：{response.status_code}")
        except Exception as e:
            print(f"❌ 运行异常：{e}")
    return []

def main():
    hosts = crawl_fofa()
    if not hosts:
        return

    os.makedirs(os.path.dirname(TARGET_FILE), exist_ok=True)
    
    existing_urls = set()
    if os.path.exists(TARGET_FILE):
        with open(TARGET_FILE, "r", encoding="utf-8") as f:
            existing_urls = {line.strip() for line in f if line.strip()}

    new_count = 0
    new_urls = []
    for host in hosts:
        full_url = f"http://{host}{CHECK_PATH}"
        if full_url not in existing_urls:
            new_urls.append(full_url)
            new_count += 1

    if new_urls:
        with open(TARGET_FILE, "a", encoding="utf-8") as f:
            for url in new_urls:
                f.write(url + "\n")
        print(f"✅ 成功追加 {new_count} 条新记录！")
    else:
        print("✨ 数据已是最新，无须追加。")

if __name__ == "__main__":
    main()
