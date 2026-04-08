import requests
import base64
import os
import json

# --- 配置区 ---
# 建议在 GitHub 仓库的 Settings -> Secrets 中设置 FOFA_EMAIL 和 FOFA_KEY
FOFA_EMAIL = os.getenv("FOFA_EMAIL")
FOFA_KEY = os.getenv("FOFA_KEY")
TARGET_FILE = "hotel/py/1000_alive.txt" # 根据你的描述路径
QUERY = '"/iptv/live" && country="CN"'
CHECK_PATH = "/iptv/live/1000.json?key=txipt"

def fetch_fofa_data():
    """通过 API 获取 FOFA 数据"""
    qbase64 = base64.b64encode(QUERY.encode()).decode()
    # 每次获取 100 条最新记录
    api_url = f"https://fofa.info/api/v1/search/all?email={FOFA_EMAIL}&key={FOFA_KEY}&qbase64={qbase64}&size=100&fields=host"
    
    try:
        response = requests.get(api_url, timeout=20)
        data = response.json()
        if data.get("error"):
            print(f"❌ FOFA API 错误: {data.get('errmsg')}")
            return []
        return data.get("results", [])
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return []

def update_file():
    # 1. 获取新数据
    new_hosts = fetch_fofa_data()
    if not new_hosts:
        print("ℹ️ 未发现新数据或 API 请求失败。")
        return

    # 2. 读取现有数据（用于比对去重）
    existing_content = set()
    if os.path.exists(TARGET_FILE):
        with open(TARGET_FILE, "r", encoding="utf-8") as f:
            existing_content = {line.strip() for line in f if line.strip()}

    # 3. 拼接并过滤
    added_urls = []
    for host in new_hosts:
        # 补全协议
        if not host.startswith('http'):
            host = f"http://{host}"
        
        full_url = f"{host.rstrip('/')}{CHECK_PATH}"
        
        # 比对去重
        if full_url not in existing_content:
            added_urls.append(full_url)
            existing_content.add(full_url)

    # 4. 追加写入
    if added_urls:
        os.makedirs(os.path.dirname(TARGET_FILE), exist_ok=True)
        with open(TARGET_FILE, "a", encoding="utf-8") as f:
            for url in added_urls:
                f.write(url + "\n")
        
        print("\n" + "="*30)
        print(f"✅ 任务完成总结:")
        print(f"🔹 本次从 FOFA 抓取: {len(new_hosts)} 条")
        print(f"🔹 过滤重复后新增: {len(added_urls)} 条")
        print(f"🔹 文件目前总条数: {len(existing_content)}")
        print("="*30)
    else:
        print("✨ 抓取到的内容已全部存在于文件中，无需更新。")

if __name__ == "__main__":
    if not FOFA_KEY:
        print("❌ 缺少 FOFA_KEY，请在 Secrets 中配置。")
    else:
        update_file()
