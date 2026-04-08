import requests
import base64
import os
import time

# --- 配置区 ---
FOFA_EMAIL = os.getenv("FOFA_EMAIL")
FOFA_KEY = os.getenv("FOFA_KEY")
TARGET_FILE = "py/1000_alive.txt"  # 路径已更正
QUERY = '"/iptv/live" && country="CN"'
CHECK_PATH = "/iptv/live/1000.json?key=txipt"

def fetch_fofa_data(retries=3):
    """通过 API 获取 FOFA 数据，加入重试机制"""
    qbase64 = base64.b64encode(QUERY.encode()).decode()
    api_url = f"https://fofa.info/api/v1/search/all?email={FOFA_EMAIL}&key={FOFA_KEY}&qbase64={qbase64}&size=100&fields=host"
    
    for i in range(retries):
        try:
            response = requests.get(api_url, timeout=40)
            data = response.json()
            if data.get("error"):
                print(f"❌ FOFA API 业务错误: {data.get('errmsg')}")
                return []
            return data.get("results", [])
        except Exception as e:
            print(f"⚠️ 第 {i+1} 次尝试失败: {e}")
            if i < retries - 1:
                time.sleep(5)
    return []

def update_file():
    # 确保目录存在
    os.makedirs(os.path.dirname(TARGET_FILE), exist_ok=True)
    
    # 如果文件不存在则创建一个空的，确保后续读取不报错
    if not os.path.exists(TARGET_FILE):
        with open(TARGET_FILE, "w", encoding="utf-8") as f:
            pass

    new_hosts = fetch_fofa_data()
    if not new_hosts:
        print("ℹ️ 本次运行未获取到新数据。")
        return

    # 读取现有内容进行比对
    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        existing_content = {line.strip() for line in f if line.strip()}

    added_urls = []
    for host in new_hosts:
        clean_host = host if host.startswith('http') else f"http://{host}"
        full_url = f"{clean_host.rstrip('/')}{CHECK_PATH}"
        
        if full_url not in existing_content:
            added_urls.append(full_url)
            existing_content.add(full_url)

    if added_urls:
        with open(TARGET_FILE, "a", encoding="utf-8") as f:
            for url in added_urls:
                f.write(url + "\n")
        print(f"✅ 成功追加 {len(added_urls)} 条新链接。")
    else:
        print("✨ 抓取到的链接已全部存在，无需更新。")

if __name__ == "__main__":
    if not FOFA_KEY:
        print("❌ 错误: 环境变量 FOFA_KEY 未设置！")
    else:
        update_file()
